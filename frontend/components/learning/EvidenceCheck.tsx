"use client";
import { useEffect,useState } from 'react';
import { studio } from '@/lib/studio';

export function EvidenceCheck({skill,phase,onComplete}:{skill:string;phase:'baseline'|'transfer'|'retention'|'reassessment';onComplete:()=>void}) {
  const [questions,setQuestions]=useState<{question:string;choices:string[]}[]>([]);
  const [answers,setAnswers]=useState<number[]>([]);
  const [score,setScore]=useState<number|null>(null);
  const [feedback,setFeedback]=useState<{correct:boolean;explanation:string}[]>([]);
  const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  useEffect(()=>{let active=true;studio.check(skill,phase).then(data=>{if(!active)return;if(data.completed){setScore(data.score??0);setQuestions(data.questions);setFeedback(data.feedback??[]);}else{setQuestions(data.questions);setAnswers(data.questions.map(()=>-1));}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[skill,phase]);
  async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);try{const result=await studio.answerCheck(skill,phase,answers);setScore(result.score);setFeedback(result.feedback);onComplete();}catch(e){setError(e instanceof Error?e.message:'Check could not be recorded.');}finally{setBusy(false);}}
  return <section className="mt-4 rounded-xl border border-brand/30 bg-surface p-5">
    <h3 className="text-lg font-semibold">{phase==='baseline'?'Before you start':phase==='transfer'?'Apply it to new cases':phase==='reassessment'?'Reassess after revision':'Seven-day recall check'}</h3>
    <p className="mt-2 text-sm text-ink-muted">Six questions. The original baseline and transfer scores stay recorded; reassessments are tracked separately. {phase==='baseline'?'This records your starting point; you do not need a passing score.':'These cases differ from the earlier check.'} Project work and these checks provide different kinds of evidence.</p>
    {error&&<p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    {score!==null?<p className="mt-4 font-medium">Recorded score: {score}%</p>:<form onSubmit={submit} className="mt-5 space-y-5">
      {questions.map((q,index)=><fieldset key={index}><legend className="font-medium">{index+1}. {q.question}</legend><div className="mt-2 space-y-2">{q.choices.map((choice,j)=><label key={j} className="flex items-start gap-3 rounded-lg border border-line bg-white p-3 text-sm"><input type="radio" required name={`evidence-${index}`} checked={answers[index]===j} onChange={()=>setAnswers(current=>current.map((value,i)=>i===index?j:value))}/><span>{choice}</span></label>)}</div></fieldset>)}
      {questions.length>0&&<button disabled={busy||answers.some(a=>a<0)} className="rounded-lg bg-brand px-4 py-2 text-sm text-white disabled:opacity-40">{busy?'Recording…':'Record my answers'}</button>}
    </form>}
    {feedback.length>0&&<ul className="mt-4 space-y-2">{feedback.map((item,index)=><li key={index} className={`text-sm ${item.correct?'text-emerald-700':'text-amber-800'}`}><p className="font-medium">{index+1}. {questions[index]?.question}</p><p className="mt-1">{item.explanation}</p></li>)}</ul>}
  </section>;
}
