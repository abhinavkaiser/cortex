export interface PracticeResult {
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
