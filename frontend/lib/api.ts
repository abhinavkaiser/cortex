import type {
  AgentResponse,
  AnswerValue,
  Certificate,
  CertificateVerify,
  Chapter,
  CompleteResponse,
  CourseDetail,
  CourseSummary,
  Curriculum,
  DailyPulse,
  EmbedResponse,
  GradeAttemptResult,
  LessonDetail,
  PendingAttempt,
  QuizAnswerResult,
  QuizAttemptResult,
  QuizAttemptSummary,
  QuizQuestionInput,
  QuizTake,
  RagResponse,
  RosterRow,
  SandboxParams,
  SandboxResult,
  TrackSummary,
  UserCourse,
  UserProgress,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options.headers,
    },
  });
  // A stored token that's expired or otherwise invalid (access tokens are
  // valid 24h, see access_token_expire_minutes) previously just threw the
  // raw "Invalid or expired token" string at whatever page happened to be
  // open, with no way to recover short of manually clearing localStorage.
  // Every page hits this the same way, so the fix belongs here, once, not
  // in each page's own error handling. Excludes the auth endpoints
  // themselves so a genuine wrong-password 401 during login still throws
  // normally instead of bouncing straight back to "/".
  if (res.status === 401 && !path.startsWith("/api/auth/") && typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    window.location.href = "/";
    throw new Error("Session expired -- redirecting to log back in.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: number; needs_onboarding: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, full_name: string) =>
    request<{ access_token: string; user_id: number; needs_onboarding: boolean }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  completeOnboarding: (track_slug: string) =>
    request<{ ok: boolean; track: unknown }>("/api/users/onboarding", {
      method: "POST",
      body: JSON.stringify({ track_slug }),
    }),

  getProgress: (userId: number) => request<UserProgress>(`/api/users/${userId}/progress`),

  completeLesson: (lesson_id: number) =>
    request<{ ok: boolean; common_core_completed: boolean }>("/api/users/lessons/complete", {
      method: "POST",
      body: JSON.stringify({ lesson_id }),
    }),

  getLesson: (lessonId: number) => request<LessonDetail>(`/api/lessons/${lessonId}`),

  getTodayPulse: () => request<DailyPulse>("/api/daily-pulse/today"),

  answerQuiz: (pulse_id: number, selected_index: number) =>
    request<QuizAnswerResult>("/api/daily-pulse/answer", {
      method: "POST",
      body: JSON.stringify({ pulse_id, selected_index }),
    }),

  executeSandboxPrompt: (params: SandboxParams) =>
    request<SandboxResult>("/api/sandbox/execute", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  embedWords: (items: string[]) =>
    request<EmbedResponse>("/api/explore/embed", {
      method: "POST",
      body: JSON.stringify({ items }),
    }),

  completeText: (prefix: string) =>
    request<CompleteResponse>("/api/explore/complete", {
      method: "POST",
      body: JSON.stringify({ prefix }),
    }),

  ragQuery: (question: string) =>
    request<RagResponse>("/api/explore/rag", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  runAgent: (goal: string) =>
    request<AgentResponse>("/api/explore/agent", {
      method: "POST",
      body: JSON.stringify({ goal }),
    }),

  getTracks: () => request<TrackSummary[]>("/api/tracks"),

  getCurriculum: (slug: string) => request<Curriculum>(`/api/tracks/${slug}/curriculum`),

  // ---- General-purpose courses -----------------------------------------

  getCourses: () => request<CourseSummary[]>("/api/courses"),

  getCourse: (slug: string) => request<CourseDetail>(`/api/courses/${slug}`),

  createCourse: (body: { slug: string; title: string; description: string; category: string }) =>
    request<CourseSummary>("/api/courses", { method: "POST", body: JSON.stringify(body) }),

  updateCourse: (
    courseId: number,
    body: { title?: string; description?: string; category?: string; is_published?: boolean; certificate_validity_days?: number | null }
  ) => request<CourseSummary>(`/api/courses/${courseId}`, { method: "PATCH", body: JSON.stringify(body) }),

  createChapter: (courseId: number, body: { title: string; objective: string; order_index: number }) =>
    request<Chapter>(`/api/courses/${courseId}/chapters`, { method: "POST", body: JSON.stringify(body) }),

  updateChapter: (courseId: number, moduleId: number, body: { title?: string; objective?: string; order_index?: number }) =>
    request<Chapter>(`/api/courses/${courseId}/chapters/${moduleId}`, { method: "PATCH", body: JSON.stringify(body) }),

  createCourseLesson: (
    courseId: number,
    moduleId: number,
    body: { slug: string; title: string; content_markdown: string; content_blocks?: object[]; order_index: number; estimated_minutes: number }
  ) => request(`/api/courses/${courseId}/chapters/${moduleId}/lessons`, { method: "POST", body: JSON.stringify(body) }),

  updateCourseLesson: (
    courseId: number,
    moduleId: number,
    lessonId: number,
    body: { title?: string; content_markdown?: string; content_blocks?: object[]; order_index?: number; estimated_minutes?: number }
  ) => request(`/api/courses/${courseId}/chapters/${moduleId}/lessons/${lessonId}`, { method: "PATCH", body: JSON.stringify(body) }),

  uploadCourseDocument: async (courseId: number, file: File): Promise<{ url: string; filename: string }> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/courses/${courseId}/upload`, {
      method: "POST",
      headers: authHeaders(), // no Content-Type -- the browser sets the multipart boundary itself
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Upload failed: ${res.status}`);
    }
    return res.json();
  },

  upsertChapterQuiz: (
    courseId: number,
    moduleId: number,
    body: { title: string; passing_score: number; questions: QuizQuestionInput[]; randomize_questions: boolean; max_attempts: number | null }
  ) => request(`/api/courses/${courseId}/chapters/${moduleId}/quiz`, { method: "POST", body: JSON.stringify(body) }),

  enrollInCourse: (courseId: number, due_at?: string | null) =>
    request<{ ok: boolean; already_enrolled: boolean }>(`/api/courses/${courseId}/enroll`, {
      method: "POST",
      body: JSON.stringify({ due_at: due_at ?? null }),
    }),

  unenrollFromCourse: (courseId: number) => request<{ ok: boolean }>(`/api/courses/${courseId}/enroll`, { method: "DELETE" }),

  getRoster: (courseId: number) => request<RosterRow[]>(`/api/courses/${courseId}/roster`),

  getUserCourses: (userId: number) => request<UserCourse[]>(`/api/users/${userId}/courses`),

  // ---- Quizzes ------------------------------------------------------------

  getQuiz: (quizId: number) => request<QuizTake>(`/api/quizzes/${quizId}`),

  submitQuizAttempt: (quizId: number, answers: AnswerValue[], question_order: number[]) =>
    request<QuizAttemptResult>(`/api/quizzes/${quizId}/attempt`, { method: "POST", body: JSON.stringify({ answers, question_order }) }),

  getQuizAttempts: (quizId: number) => request<QuizAttemptSummary[]>(`/api/quizzes/${quizId}/attempts`),

  // ---- Instructor grading queue (short_answer questions) -------------------

  getPendingAttempts: (quizId: number) => request<PendingAttempt[]>(`/api/quizzes/${quizId}/pending-attempts`),

  gradeAttempt: (attemptId: number, body: { score: number; passed: boolean }) =>
    request<GradeAttemptResult>(`/api/quiz-attempts/${attemptId}/grade`, { method: "POST", body: JSON.stringify(body) }),

  // ---- Certificates ---------------------------------------------------------

  getMyCertificates: () => request<Certificate[]>("/api/certificates/me"),

  verifyCertificate: (code: string) => request<CertificateVerify>(`/api/certificates/verify/${code}`),

  downloadCertificatePdf: async (certificateId: number): Promise<Blob> => {
    const res = await fetch(`${API_URL}/api/certificates/${certificateId}/pdf`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`Could not download certificate: ${res.status}`);
    return res.blob();
  },
};
