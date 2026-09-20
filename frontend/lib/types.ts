// Mirrors backend/app/schemas/*.py -- kept hand-in-sync rather than
// codegen'd for this scaffold; if the schemas drift, generating this file
// from the FastAPI OpenAPI spec (openapi-typescript) is the natural next
// step once the API stabilizes.

export type TrackSlug = "leader" | "practitioner" | "developer";

export interface Track {
  id: number;
  slug: TrackSlug;
  name: string;
}

export interface LessonProgress {
  lesson_id: number;
  lesson_title: string;
  completed_at: string;
}

export interface Lesson {
  id: number;
  title: string;
  estimated_minutes: number;
  order_index: number;
  completed: boolean;
  module_id: number | null;
  module_title: string | null;
}

export interface LessonDetail {
  id: number;
  title: string;
  content_markdown: string;
  estimated_minutes: number;
  completed: boolean;
  track_slug: TrackSlug | null;
  module_title: string | null;
}

export interface UserProgress {
  user_id: number;
  email: string;
  track: Track | null;
  common_core_completed: boolean;
  common_core_completed_at: string | null;
  common_core_lessons_total: number;
  common_core_lessons_completed: number;
  track_lessons_total: number;
  track_lessons_completed: number;
  common_core_lessons: Lesson[];
  track_lessons: Lesson[];
  completed_lessons: LessonProgress[];
}

export interface DailyPulse {
  id: number;
  pulse_date: string;
  track_slug: TrackSlug | null;
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
