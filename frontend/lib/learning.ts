import type { Assessment } from "./studio";
export interface PracticeResult {
  id: number;
  assessment: Assessment | null;
  score: number;
  answers: number[];
  reflection: string;
  submitted_at: string;
  feedback: { correct: boolean; explanation: string }[];
  reference: string;
  rubric: string[];
  practice_complete: boolean;
}
export interface LearningUnit {
  mastered: boolean;
  presentation: "practice_first" | "explanation_first";
  version: string;
  objective: string;
  prerequisites: string;
  sources: { title: string; url: string }[];
  reviewed_on: string;
  review_due: string;
  status: "reviewed" | "review_due" | "changed_since_review";
  stage: string;
  best_score: number | null;
  latest_attempt: PracticeResult | null;
  exercise: {
    title: string;
    scenario: string;
    questions: { question: string; choices: string[] }[];
    reflection_prompt: string;
  };
}
export interface PathUnit {
  assessed: boolean;
  lesson_id: number;
  title: string;
  stage: string;
  objective: string;
  minutes: number;
  course_slug: string;
  status: LearningUnit["status"];
  practice_score: number | null;
}
export interface CurriculumUpdate {
  title: string;
  url: string;
  summary: string;
  source: string;
  published_at: string;
}
