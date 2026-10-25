"use client";
import {useEffect,useState} from 'react';
import {studio,type CourseAmendment} from '@/lib/studio';

function AmendmentCard({item,managedPractice}:{item:CourseAmendment;managedPractice:boolean}){
  const [selected,setSelected]=useState(item.last_answer?.selected??-1);
  const [answer,setAnswer]=useState(item.last_answer);
  const [error,setError]=useState('');
  async function submit(){try{const result=await studio.answerAmendment(item.id,selected);setAnswer({...result,selected});}catch(e){setError(e instanceof Error?e.message:'Answer could not be recorded.');}}
  return <article className="mt-4 rounded-lg border border-line p-4">
    <h3 className="font-medium">{item.title}</h3>
    <p className="mt-1 text-xs text-ink-muted">Published {item.published_at.slice(0,10)} · The teaching update is included in the worked explanation.</p>
    <details className="mt-3 text-sm"><summary className="cursor-pointer text-brand">Inspect the supporting evidence</summary>
      {item.evidence.map((entry,index)=><div key={index} className="mt-3"><p>{entry.claim}</p><blockquote className="mt-1 border-l-2 border-brand pl-3 text-ink-muted">“{entry.quote}”</blockquote><a href={entry.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-brand underline">Primary source ↗</a></div>)}
    </details>
    {managedPractice?<p className="mt-3 text-sm">The update task is part of this lesson&apos;s current practice. Earlier versions remain in your learning history.</p>:<fieldset className="mt-4"><legend className="font-medium">{item.question.question}</legend><div className="mt-2 space-y-2">{item.question.choices.map((choice,index)=><label key={index} className="flex gap-3 text-sm"><input type="radio" name={`amendment-${item.id}`} checked={selected===index} onChange={()=>{setSelected(index);setAnswer(null);}}/>{choice}</label>)}</div><button onClick={submit} disabled={selected<0} className="mt-3 rounded-lg border border-brand px-3 py-2 text-sm text-brand disabled:opacity-40">Check my answer</button>{answer&&<p className={`mt-3 text-sm ${answer.correct?'text-emerald-700':'text-amber-800'}`}>{answer.feedback}</p>}</fieldset>}
    {error&&<p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
  </article>;
}
export function PublishedAmendments({lessonId,managedPractice}:{lessonId:number;managedPractice:boolean}){
 const [items,setItems]=useState<CourseAmendment[]>([]);const [error,setError]=useState('');
 useEffect(()=>{let active=true;studio.amendments(lessonId).then(data=>{if(active)setItems(data);}).catch(()=>{if(active)setError('Published revisions could not be loaded.');});return()=>{active=false;};},[lessonId]);
 if(!items.length&&!error)return null;
 return <section className="mt-8 rounded-xl border border-brand/30 p-5"><h2 className="text-lg font-semibold">Evidence-checked course revisions</h2><p className="mt-2 text-xs text-ink-muted">These teaching additions passed source-quote checks and a separate model review. Inspect the evidence; reported vendor claims remain attributed to their source.</p>{items.map(item=><AmendmentCard key={item.id} item={item} managedPractice={managedPractice}/>)}{error&&<p className="mt-2 text-sm text-amber-800">{error}</p>}</section>;
}
