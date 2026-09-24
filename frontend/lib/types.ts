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

export type LessonBlock = TextBlock | CalloutBlock | CheckBlock | DiagramBlockType | CalculatorBlock | ImageBlock;

export interface LessonDetail {
  id: number;
  title: string;
  content_markdown: string;
  content_blocks: LessonBlock[];
  estimated_minutes: number;
  completed: boolean;
  track_slug: TrackSlug | null;
  module_title: string | null;
}

export type UserRole = "learner" | "instructor" | "admin";

export interface UserProgress {
  user_id: number;
  email: string;
  role: UserRole;
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

export interface TrackSummary {
  slug: TrackSlug;
  name: string;
  description: string;
  lesson_count: number;
}

export interface CurriculumModule {
  id: number;
  title: string;
  objective: string;
  lessons: Lesson[];
}

export interface Curriculum {
  track: TrackSummary;
  modules: CurriculumModule[];
  ungrouped_lessons: Lesson[];
}

// ---- General-purpose Course system (mirrors backend/app/schemas/course.py)
// Coexists with Track/Curriculum above -- a Course is arbitrary,
// instructor-authored content built from the same Module/Lesson tables,
// not a Track. See backend/app/models/course.py for the schema rationale.

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

export interface QuizQuestionTake {
  question: string;
  choices: string[];
}

export interface QuizTake {
  id: number;
  title: string;
  passing_score: number;
  questions: QuizQuestionTake[];
}

export interface QuestionResult {
  correct: boolean;
  correct_index: number;
  selected_index: number;
}

export interface QuizAttemptResult {
  score: number;
  passed: boolean;
  passing_score: number;
  results: QuestionResult[];
  course_completed: boolean;
}

export interface QuizAttemptSummary {
  id: number;
  score: number;
  passed: boolean;
  attempted_at: string;
}

export interface Certificate {
  id: number;
  course_id: number;
  course_title: string;
  certificate_code: string;
  issued_at: string;
}

export interface CertificateVerify {
  learner_name: string;
  course_title: string;
  issued_at: string;
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
  question: string;
  choices: string[];
  correct_index: number;
}
