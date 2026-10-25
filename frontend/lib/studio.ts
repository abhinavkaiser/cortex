import type {Preparation} from "./types";
import { request } from './api';

export interface Assessment {
  id: number; kind: string; status: string; passed: boolean; version: string;
  result: { score?: number; message?: string; explanation?: string; note?: string;
    metrics?:Record<string,unknown>;scope?:string;
    results?:{baseline:{correct:boolean[];cases:unknown[]};candidate:{correct:boolean[];cases:unknown[]}};
    reviews?: { model: string; summary: string; next_steps: string[]; criteria: {id:string;score:number;evidence:string;feedback:string}[] }[] };
  created_at: string; finished_at: string | null;
}
export interface Benchmark { checks: Record<string, boolean>; metrics: Record<string, unknown>; scope: string }
export interface EvidenceState {
  skill:string; baseline:number|null; transfer:number|null; retention:number|null;
  reassessment_count:number; reassessment_best:number|null; transfer_change_points:number|null; retention_due:string|null; retention_available:boolean; note:string; items_per_check:number;
}
export interface ProjectSummary {
  slug:string; title:string; audience:string; hours:number; skill:string; brief:string; course:string;
  version:string; milestones_passed:number; milestones_total:number; completed:boolean;
}
export interface ProjectDetail extends ProjectSummary {
  preparation?:Preparation|null;
  evidence:string; evidence_check:EvidenceState;
  milestones:{index:number;title:string;task:string;starter:Record<string,unknown>;rubric:{id:string;description:string}[];
    reading:{id:number;title:string}[];passed:boolean;draft:{artifact:string;report:string;updated_at:string}|null;
    experiments:{id:number;artifact:Record<string,unknown>;benchmark:Benchmark;created_at:string;assessment:Assessment|null}[];
    submissions:{id:number;report:string;artifact:Record<string,unknown>;benchmark:Benchmark;submitted_at:string;assessment:Assessment|null}[]}[];
}
export interface LearningOutcomes {
  evidence:EvidenceState[];
  engagement:{active_minutes:number;active_days:number;practice_attempts:number;revisions:number;first_attempt_decision_mean:number|null;note:string};
  written_work:{graded:number;passed:number};
}
export interface StudyStatus {
  protocol:string;consent:boolean;arm:string;primary_outcome:string;comparison:string;pilot_target:string;privacy:string;limitation:string;
}
export interface StudioStatus {worker_online:boolean;grading_calibrated:boolean;worker_last_seen:string|null;calibration_date:string|null;queued:number;published_updates:number;model_ids:string[]}
export interface CourseAmendment {
  id:number;title:string;markdown:string;published_at:string;evidence:{claim:string;quote:string;url:string}[];
  question:{question:string;choices:string[]};last_answer:{selected:number;correct:boolean;feedback:string}|null;
}
export const studio = {
  projects:()=>request<ProjectSummary[]>('/api/studio/projects'),
  project:(slug:string)=>request<ProjectDetail>(`/api/studio/projects/${slug}`),
  submit:(slug:string,version:string,milestone:number,artifact:Record<string,unknown>,report:string)=>
    request<{submission_id:number;benchmark:Benchmark;assessment:Assessment}>(`/api/studio/projects/${slug}/submissions`,{method:'POST',body:JSON.stringify({version,milestone,artifact,report})}),
  saveDraft:(slug:string,version:string,milestone:number,artifact_text:string,report:string)=>request<{saved:boolean;updated_at:string}>(`/api/studio/projects/${slug}/draft`,{method:'PUT',body:JSON.stringify({version,milestone,artifact_text,report})}),
  promptExperiment:(slug:string,version:string,baseline:string,candidate:string)=>request<Assessment>(`/api/studio/projects/${slug}/prompt-experiment`,{method:'POST',body:JSON.stringify({version,baseline,candidate})}),
  experiment:(slug:string,version:string,milestone:number,artifact:Record<string,unknown>)=>request<{id:number;benchmark:Benchmark;note:string}>(`/api/studio/projects/${slug}/experiment`,{method:'POST',body:JSON.stringify({version,milestone,artifact})}),
  history:()=>request<{title:string;assessment:Assessment}[]>('/api/studio/history'),
  job:(id:number)=>request<Assessment>(`/api/studio/jobs/${id}`),
  retry:(id:number)=>request<Assessment>(`/api/studio/jobs/${id}/retry`,{method:'POST'}),
  appeal:(id:number,reason:string)=>request<{id:number;status:string}>(`/api/studio/jobs/${id}/appeal`,{method:'POST',body:JSON.stringify({reason})}),
  assessPractice:(id:number)=>request<Assessment>(`/api/studio/practices/${id}/feedback`,{method:'POST'}),
  check:(skill:string,phase:string)=>request<{completed:boolean;score?:number;questions:{question:string;choices:string[]}[];feedback?:{correct:boolean;explanation:string}[]}>(`/api/studio/checks/${skill}/${phase}`),
  answerCheck:(skill:string,phase:string,answers:number[])=>request<{score:number;feedback:{correct:boolean;explanation:string}[];state:EvidenceState}>(`/api/studio/checks/${skill}`,{method:'POST',body:JSON.stringify({phase,answers})}),
  outcomes:()=>request<LearningOutcomes>('/api/studio/outcomes'),
  status:()=>request<StudioStatus>('/api/studio/status'),
  study:()=>request<StudyStatus>('/api/studio/study'),
  consent:(consent:boolean)=>request<StudyStatus>('/api/studio/study',{method:'POST',body:JSON.stringify({consent})}),
  cohort:()=>request<{status:string;conclusion:string;note:string;arms:Record<string,{enrolled:number;baseline_participants:number;transfer_participants:number;retention_participants:number;retention_mean:number|null;missing_retention:number}>}>('/api/studio/study/report'),
  activity:(lesson_id:number,seconds:number)=>request('/api/studio/activity',{method:'POST',body:JSON.stringify({lesson_id,seconds})}),
  amendments:(id:number)=>request<CourseAmendment[]>(`/api/studio/lessons/${id}/amendments`),
  answerAmendment:(id:number,selected:number)=>request<{correct:boolean;feedback:string}>(`/api/studio/amendments/${id}/answer`,{method:'POST',body:JSON.stringify({selected})}),
  reviewQueue:()=>request<{assessment:Assessment;work:{title:string;case:string;task:string;report?:string;rubric?:{id:string;description:string}[]};appeal:{id:number;reason:string}|null}[]>('/api/studio/review'),
  review:(id:number,passed:boolean,score:number,explanation:string)=>request<Assessment>(`/api/studio/jobs/${id}/review`,{method:'POST',body:JSON.stringify({passed,score,explanation})}),
  withdraw:(id:number,reason:string)=>request(`/api/studio/amendments/${id}/withdraw`,{method:'POST',body:JSON.stringify({reason})}),
};
