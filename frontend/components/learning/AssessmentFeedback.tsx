"use client";
import { useEffect, useState } from 'react';
import { studio, type Assessment, type StudioStatus } from '@/lib/studio';

export function AssessmentFeedback({ job, onChange }: {job:Assessment;onChange:(job:Assessment)=>void}) {
  const [error,setError]=useState('');
  const [reason,setReason]=useState('');
  const [appealed,setAppealed]=useState(false);
  const [health,setHealth]=useState<StudioStatus|null>(null);
  useEffect(()=>{studio.status().then(setHealth).catch(()=>{});},[job.id,job.status]);
  useEffect(()=>{
    if(!['queued','running'].includes(job.status))return;
    let active=true,busy=false;
    const poll=async()=>{if(busy)return;busy=true;try{const next=await studio.job(job.id);if(active){onChange(next);setError('');}}catch{if(active)setError('Feedback status could not be loaded. Your work remains saved.');}finally{busy=false;}};
    const timer=setInterval(poll,5000);
    return()=>{active=false;clearInterval(timer);};
  },[job.id,job.status,onChange]);
  async function retry(){try{onChange(await studio.retry(job.id));setError('');}catch(e){setError(e instanceof Error?e.message:'Retry failed.');}}
  async function appeal(){try{await studio.appeal(job.id,reason);setAppealed(true);setError('');}catch(e){setError(e instanceof Error?e.message:'Review request failed.');}}
  const waiting=['queued','running'].includes(job.status);
  return <section className="mt-5 rounded-xl border border-line bg-white p-5" aria-live="polite">
    <h3 className="font-semibold">Reasoning feedback</h3>
    {waiting?<p className="mt-2 text-sm">{job.status==='queued'?'Your work is saved and queued for assessment.':'The graders are checking your work against the rubric.'} This can take a few minutes. You can leave and return.{health&&(!health.worker_online||!health.grading_calibrated)&&<span className="mt-2 block text-amber-800">Assessment processing is currently paused or unavailable. Your work remains saved; no pass will be awarded until verified assessment completes.</span>}</p>:<>
      <p className="mt-2 text-sm font-medium">{job.status==='failed'?'Assessment unavailable':job.status==='needs_review'?'Instructor review needed':job.passed?'Rubric requirements met':`Revise and resubmit${job.result.score!==undefined?` · ${job.result.score}%`:''}`}</p>
      {job.result.message&&<p className="mt-2 text-sm">{job.result.message}</p>}
      {job.result.explanation&&<p className="mt-2 whitespace-pre-line text-sm">Instructor: {job.result.explanation}</p>}
      {job.result.reviews?.map(review=><details key={review.model} className="mt-4 rounded-lg border border-line p-3" open>
        <summary className="cursor-pointer text-sm font-medium">Review: {review.model}</summary>
        <p className="mt-2 text-sm">{review.summary}</p>
        <ul className="mt-3 space-y-3">{review.criteria.map(criterion=><li key={criterion.id} className="text-sm">
          <p className="font-medium">{criterion.id.replace('criterion_','Criterion ')} · {criterion.score}/4</p>
          {criterion.evidence&&<blockquote className="mt-1 border-l-2 border-brand pl-3 text-ink-muted">“{criterion.evidence}”</blockquote>}
          <p className="mt-1">{criterion.feedback}</p>
        </li>)}</ul>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm">{review.next_steps.map(step=><li key={step}>{step}</li>)}</ol>
      </details>)}
      {job.result.note&&<p className="mt-3 text-xs text-ink-muted">{job.result.note}</p>}
      {job.status==='failed'&&<button onClick={retry} className="mt-3 text-sm text-brand underline">Retry assessment</button>}
      {!appealed?<details className="mt-4"><summary className="cursor-pointer text-sm text-brand">Request instructor review</summary>
        <label className="mt-2 block text-sm">Explain which criterion or evidence needs review<textarea rows={3} minLength={40} maxLength={4000} value={reason} onChange={e=>setReason(e.target.value)} className="mt-2 w-full rounded-lg border border-line p-3"/></label>
        <button onClick={appeal} disabled={reason.trim().length<40} className="mt-2 rounded-lg border border-brand px-3 py-2 text-sm text-brand disabled:opacity-40">Submit review request</button>
      </details>:<p className="mt-3 text-sm text-brand">Instructor review requested. Your original assessment and work are retained.</p>}
    </>}
    {error&&<p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
  </section>;
}
