import type { DailyPulse, LessonDetail, QuizAnswerResult, SandboxParams, SandboxResult, UserProgress } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
};
