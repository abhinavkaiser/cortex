// Mirrors backend/app/schemas/*.py -- kept hand-in-sync rather than
// codegen'd for this scaffold; if the schemas drift, generating this file
// from the FastAPI OpenAPI spec (openapi-typescript) is the natural next
// step once the API stabilizes.

// Tracks are no longer a learner-facing concept (see README's "Courses vs.
// Tracks") -- the former AI Leader/Practitioner/Developer curriculum now
// lives as ordinary Courses. TrackSlug survives only because DailyPulse
// (an unrelated feature -- see backend/app/models/track.py) is still
// generated and labeled per track.
export type TrackSlug = "leader" | "practitioner" | "developer";

export interface Lesson {
  id: number;
  title: string;
  estimated_minutes: number;
  order_index: number;
  completed: boolean;
  module_id: number | null;
  module_title: string | null;
}

// Discriminated union mirroring backend/app/agents/lesson_blocks.py's
// BLOCK_SCHEMA -- the closed set of shapes validate_and_clean_blocks()
// guarantees every stored block matches, so this can be strict rather than
// defensive.
export interface TextBlock {
  type: "text";
  markdown: string;
}

export interface CalloutBlock {
  type: "callout";
  style: "insight" | "warning";
  markdown: string;
}

export interface CheckBlock {
  type: "check";
  question: string;
  choices: string[];
  correct_index: number;
  explanation: string;
}

export interface TiersDiagram {
  type: "diagram";
  shape: "tiers";
  title: string;
  items: { label: string; description: string }[];
}

export interface ComparisonDiagram {
  type: "diagram";
  shape: "comparison";
  title: string;
  columns: string[];
  rows: { label: string; values: string[] }[];
}

export interface MatrixDiagram {
  type: "diagram";
  shape: "matrix";
  title: string;
  x_label: string;
  y_label: string;
  quadrants: { position: "top-left" | "top-right" | "bottom-left" | "bottom-right"; label: string; description: string }[];
}

export interface CycleDiagram {
  type: "diagram";
  shape: "cycle";
  title: string;
  steps: { label: string; description: string }[];
}

export type DiagramBlockType = TiersDiagram | ComparisonDiagram | MatrixDiagram | CycleDiagram;

export interface CalculatorInput {
  key: string;
  label: string;
  default: number;
  min: number;
  max: number;
  step: number;
  unit: string;
}

export interface CalculatorBlock {
  type: "calculator";
  title: string;
  description: string;
  inputs: CalculatorInput[];
  formula: string;
  output_label: string;
  output_format: "currency" | "number" | "percent";
}

export interface ImageBlock {
  type: "image";
  url: string;
  alt: string;
  caption: string;
  attribution: string;
}

// A YouTube/Vimeo URL is parsed client-side (lib/videoEmbed.ts) into an
// embed URL and rendered via <iframe>; anything else (a direct file URL)
// falls back to a native <video> tag. transcript is optional plain text.
export interface VideoBlock {
  type: "video";
  title: string;
  url: string;
  transcript: string;
}

// url comes from POST /api/courses/{id}/upload (see lib/api.ts's
// uploadCourseDocument) -- a /static/... path this app serves itself, same
// convention ImageBlock's url already uses.
export interface DocumentBlock {
  type: "document";
  title: string;
  url: string;
  filename: string;
}

// An external URL this app doesn't control or host -- rendered as a
// clearly-labeled outbound card, never auto-embedded (unlike video/document
// above).
export interface LinkBlock {
  type: "link";
  title: string;
  url: string;
  description: string;
}

export type LessonBlock = TextBlock | CalloutBlock | CheckBlock | DiagramBlockType | CalculatorBlock | ImageBlock | VideoBlock | DocumentBlock | LinkBlock;

export interface LessonDetail {
  id: number;
  title: string;
  content_markdown: string;
  content_blocks: LessonBlock[];
  estimated_minutes: number;
  completed: boolean;
  module_title: string | null;
}

export type UserRole = "learner" | "instructor" | "admin";

// Identity/role lookup only now -- see backend UserProgressOut's docstring.
// Per-course progress lives at UserCourse/CourseDetail instead, since a
// learner can be enrolled in any number of courses, not one track.
export interface UserProgress {
  user_id: number;
  email: string;
  role: UserRole;
}

export interface DailyPulse {
  id: number;
  pulse_date: string;
  track_slug: TrackSlug | null;
  // Label for the track this pulse was written for -- see api.ts's
  // getTodayPulse, which now returns one pulse per track (a user no
  // longer has a single assigned track to scope this to).
  track_name: string | null;
  summary: string;
  sandbox_exercise: string;
  quiz_question: string;
  quiz_choices: string[];
  source_urls: string[];
  created_at: string;
}

export interface QuizAnswerResult {
  correct: boolean;
  correct_index: number;
}

export interface SandboxParams {
  prompt: string;
  model: string;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
}

export interface SandboxResult {
  attempt_id: number;
  response_text: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  served_from_cache: boolean;
}

export interface EmbedPoint {
  label: string;
  x: number;
  y: number;
}

export interface EmbedResponse {
  points: EmbedPoint[];
  closest_pair: [number, number];
  closest_similarity: number;
  farthest_pair: [number, number];
  farthest_similarity: number;
}

export interface CompleteResponse {
  completion: string;
}

export interface RagResult {
  text: string;
  similarity: number;
}

export interface RagResponse {
  retrieved: RagResult[];
  ungrounded_answer: string;
  grounded_answer: string;
}

export interface AgentStep {
  thought_raw: string;
  tool: string | null;
  tool_input: string | null;
  observation: string | null;
}

export interface AgentResponse {
  steps: AgentStep[];
  final_answer: string;
}

// ---- General-purpose Course system (mirrors backend/app/schemas/course.py)
// The only content model now -- see backend/app/models/course.py. Used to
// coexist with a separate Track/Curriculum system; that curriculum was
// merged in as ordinary Courses (see README's "Formerly Tracks, now
// migrated into Courses").

export interface CourseSummary {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: string;
  is_published: boolean;
  instructor_id: number;
  chapter_count: number;
  lesson_count: number;
  estimated_total_minutes: number;
  certificate_validity_days: number | null;
  enrolled: boolean;
  progress_pct: number | null;
  completed_at: string | null;
}

export interface CourseLessonOut {
  id: number;
  title: string;
  order_index: number;
  estimated_minutes: number;
  completed: boolean;
}

export interface QuizSummary {
  id: number;
  title: string;
  passing_score: number;
  question_count: number;
  best_score: number | null;
  passed: boolean;
  randomize_questions: boolean;
  max_attempts: number | null;
}

export interface Chapter {
  id: number;
  title: string;
  objective: string;
  order_index: number;
  lessons: CourseLessonOut[];
  quiz: QuizSummary | null;
}

export interface CourseDetail {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: string;
  is_published: boolean;
  instructor_id: number;
  certificate_validity_days: number | null;
  estimated_total_minutes: number;
  enrolled: boolean;
  progress_pct: number | null;
  completed_at: string | null;
  certificate_code: string | null;
  chapters: Chapter[];
}

export interface RosterRow {
  user_id: number;
  email: string;
  full_name: string;
  enrolled_at: string;
  progress_pct: number;
  completed_at: string | null;
}

export type QuestionType = "multiple_choice" | "multi_select" | "true_false" | "short_answer";

// One answer's value: an int (multiple_choice/true_false selected index),
// number[] (multi_select selected indices), a string (short_answer free
// text), or null (unanswered). Mirrors backend AnswerValue.
export type AnswerValue = number | number[] | string | null;

export interface QuizQuestionTake {
  original_index: number;
  type: QuestionType;
  question: string;
  choices: string[];
}

export interface QuizTake {
  id: number;
  title: string;
  passing_score: number;
  max_attempts: number | null;
  attempts_used: number;
  questions: QuizQuestionTake[];
}

export interface QuestionResult {
  type: QuestionType;
  correct: boolean | null; // null for a short_answer question -- pending instructor review
  selected: AnswerValue;
  correct_index: number | null;
  correct_indices: number[] | null;
}

export type QuizAttemptStatus = "graded" | "pending";

export interface QuizAttemptResult {
  score: number;
  passed: boolean;
  status: QuizAttemptStatus;
  passing_score: number;
  results: QuestionResult[];
  course_completed: boolean;
}

export interface QuizAttemptSummary {
  id: number;
  score: number;
  passed: boolean;
  status: QuizAttemptStatus;
  attempted_at: string;
}

// ---- Instructor grading queue (short_answer questions) ---------------

export interface PendingAttemptQuestion {
  type: QuestionType;
  question: string;
  sample_answer?: string;
}

export interface PendingAttempt {
  id: number;
  user_id: number;
  user_email: string;
  user_full_name: string;
  attempted_at: string;
  questions: PendingAttemptQuestion[];
  answers: AnswerValue[];
}

export interface GradeAttemptResult {
  id: number;
  score: number;
  passed: boolean;
  status: QuizAttemptStatus;
  course_completed: boolean;
}

export interface Certificate {
  id: number;
  course_id: number;
  course_title: string;
  certificate_code: string;
  issued_at: string;
  expires_at: string | null;
  is_expired: boolean;
}

export interface CertificateVerify {
  learner_name: string;
  course_title: string;
  issued_at: string;
  expires_at: string | null;
  is_expired: boolean;
}

export interface UserCourse {
  course_id: number;
  slug: string;
  title: string;
  category: string;
  progress_pct: number;
  enrolled_at: string;
  due_at: string | null;
  completed_at: string | null;
}

export interface QuizQuestionInput {
  type: QuestionType;
  question: string;
  choices: string[];
  correct_index: number | null; // multiple_choice / true_false
  correct_indices: number[]; // multi_select
  sample_answer: string; // short_answer -- shown to the instructor grading it
}
