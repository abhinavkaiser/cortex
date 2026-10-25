"use client";
import {useCallback,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {useParams} from 'next/navigation';
import {API_URL} from '@/lib/api';
import {studio,type Assessment,type Benchmark,type ProjectDetail} from '@/lib/studio';
import {AssessmentFeedback} from '@/components/learning/AssessmentFeedback';
import {PromptExperiment} from '@/components/learning/PromptExperiment';
import {PreparationCard} from '@/components/learning/PreparationCard';
import {EvidenceCheck} from '@/components/learning/EvidenceCheck';

export default function ProjectPage(){
 const {slug}=useParams<{slug:string}>();
 const [project,setProject]=useState<ProjectDetail|null>(null);
 const [selected,setSelected]=useState(0);
 const [drafts,setDrafts]=useState<Record<number,{artifact:string;report:string}>>({});
 const [dirty,setDirty]=useState<Record<number,number>>({});const editCounter=useRef(0);const activeSlug=useRef(slug);const [saved,setSaved]=useState('');
 const [preview,setPreview]=useState<Benchmark|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 const [recheck,setRecheck]=useState(false);
 const [showBaseline,setShowBaseline]=useState(false);const [showTransfer,setShowTransfer]=useState(false);
 const load=useCallback(async()=>{
   const data=await studio.project(slug);if(activeSlug.current!==slug)return;setProject(data);
   setDrafts(current=>{const next={...current};for(const item of data.milestones)if(!next[item.index])next[item.index]={artifact:item.draft?.artifact??JSON.stringify(item.submissions[0]?.artifact??item.starter,null,2),report:item.draft?.report??item.submissions[0]?.report??''};return next;});
 },[slug]);
 useEffect(()=>{activeSlug.current=slug;setProject(null);setDrafts({});setDirty({});setSelected(0);setSaved('');load().catch(e=>setError(e.message));},[load,slug]);
 const changed=useCallback((job:Assessment)=>{setProject(current=>current?{...current,milestones:current.milestones.map(item=>({...item,submissions:item.submissions.map(work=>work.assessment?.id===job.id?{...work,assessment:job}:work)}))}:current);if(!['queued','running'].includes(job.status))load().catch(()=>{});},[load]);
 function update(field:'artifact'|'report',value:string){const edit=++editCounter.current;setDirty(current=>({...current,[selected]:edit}));setSaved('Unsaved changes');setDrafts(current=>({...current,[selected]:{...current[selected],[field]:value}}));}
 useEffect(()=>{
   if(!project)return;
   const pending=Object.keys(dirty).map(Number).filter(index=>dirty[index]&&drafts[index]);
   if(!pending.length)return;
   const timer=setTimeout(()=>{
     Promise.all(pending.map(index=>studio.saveDraft(slug,project.version,index,drafts[index].artifact,drafts[index].report))).then(()=>{
       setDirty(current=>{const next={...current};for(const index of pending)if(current[index]===dirty[index])next[index]=0;return next;});setSaved('Draft saved to your account');
     }).catch(()=>{setSaved('Draft could not be saved.');setError('Draft could not be saved. Keep this page open and edit again to retry.');});
   },2000);
   return()=>clearTimeout(timer);
 },[drafts,dirty,project,slug]);
 function configuration(){const value=JSON.parse(drafts[selected].artifact);if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('Configuration must be a JSON object.');return value as Record<string,unknown>;}
 async function experiment(){if(!project)return;setBusy(true);setError('');try{const result=await studio.experiment(slug,project.version,selected,configuration());setPreview(result.benchmark);await load();}catch(e){setError(e instanceof Error?e.message:'Experiment failed.');}finally{setBusy(false);}}
 async function submit(e:React.FormEvent){e.preventDefault();if(!project)return;setBusy(true);setError('');try{await studio.submit(slug,project.version,selected,configuration(),drafts[selected].report);await load();}catch(e){setError(e instanceof Error?e.message:'Submission failed.');}finally{setBusy(false);}}
 if(!project)return <main className="mx-auto max-w-3xl px-6 py-12">{error||'Loading project…'}</main>;
 const item=project.milestones[selected];const draft=drafts[selected];const latest=item.submissions[0];
 const baseline=project.evidence_check.baseline!==null;const allPassed=project.milestones.every(m=>m.passed);
 const unlocked=project.milestones.slice(0,selected).every(m=>m.passed);
 return <main className="mx-auto max-w-3xl px-6 py-12">
   <Link href="/dashboard/projects" className="text-sm text-brand">← Projects</Link>
   <p className="mt-4 text-xs uppercase tracking-wide text-brand">{project.audience}</p><h1 className="mt-2 text-3xl font-semibold">{project.title}</h1>
   <p className="mt-3 text-sm leading-relaxed text-ink-muted">{project.brief}</p>
   <PreparationCard preparation={project.preparation} />
   <section className="mt-6 rounded-xl border border-line p-5"><h2 className="font-semibold">Your evidence pack</h2><p className="mt-2 whitespace-pre-line text-sm leading-relaxed">{project.evidence}</p><a href={`${API_URL}/api/learning/lab-pack`} className="mt-3 inline-block text-sm text-brand underline">Download runnable code, datasets and tests</a></section>
   {!baseline||showBaseline?<><EvidenceCheck skill={project.skill} phase="baseline" onComplete={()=>{setShowBaseline(true);load().catch(()=>{});}}/>{baseline&&<button onClick={()=>setShowBaseline(false)} className="mt-3 text-sm text-brand underline">Continue to the project →</button>}</>:<p className="mt-4 text-sm">Starting check: {project.evidence_check.baseline}% · Original transfer: {project.evidence_check.transfer??'not taken'}{project.evidence_check.transfer!==null?'%':''}</p>}
   <div className="mt-8 flex flex-wrap gap-2">{project.milestones.map(m=><button key={m.index} onClick={()=>{setSelected(m.index);setPreview(null);}} aria-pressed={m.index===selected} className={`rounded-lg border px-3 py-2 text-sm ${selected===m.index?'border-brand bg-brand text-white':'border-line'}`}>{m.index+1}. {m.title}{m.passed?' ✓':''}</button>)}</div>
   <section className="mt-5 rounded-2xl border border-line p-6">
     <h2 className="text-xl font-semibold">{selected+1}. {item.title}</h2><p className="mt-3 whitespace-pre-line leading-relaxed">{item.task}</p>
     <h3 className="mt-5 font-semibold">What the grader checks</h3><ul className="mt-2 list-disc space-y-2 pl-5 text-sm">{item.rubric.map(c=><li key={c.id}>{c.description}</li>)}</ul>
     {item.reading.length>0&&<details className="mt-4"><summary className="cursor-pointer text-sm text-brand">Related lessons</summary><ul className="mt-2 space-y-2">{item.reading.map(lesson=><li key={lesson.id}><Link href={`/dashboard/lessons/${lesson.id}`} className="text-sm text-brand underline">{lesson.title}</Link></li>)}</ul></details>}
     {saved&&<p className="mt-4 text-xs text-ink-muted" aria-live="polite">{Object.values(dirty).some(Boolean)?'Saving draft…':saved}</p>}
     {project.slug==='team-prompt-evaluation'&&selected===1&&<PromptExperiment slug={slug} version={project.version} initialJob={item.experiments.find(e=>e.assessment?.kind==='prompt_experiment')?.assessment??null} onMeasured={values=>{update('artifact',JSON.stringify(values,null,2));load().catch(()=>{});}}/>}
     {draft&&<form onSubmit={submit} className="mt-6 space-y-5">
       <div><label htmlFor="artifact" className="font-medium">Experiment configuration (JSON)</label><p className="mt-1 text-xs text-ink-muted">Start from the supplied example. The server executes this bounded configuration, not arbitrary submitted code.</p><textarea id="artifact" rows={8} value={draft.artifact} onChange={e=>update('artifact',e.target.value)} className="mt-2 w-full rounded-lg border border-line bg-surface p-3 font-mono text-sm"/></div>
       <button type="button" onClick={experiment} disabled={busy} className="rounded-lg border border-brand px-4 py-2 text-sm text-brand disabled:opacity-40">{busy?'Working…':'Run and record development experiment'}</button>
       {preview&&<div className="rounded-lg bg-surface p-4"><p className="text-sm font-medium">Development result</p><pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify(preview.metrics,null,2)}</pre><p className="mt-2 text-xs text-ink-muted">{preview.scope}</p></div>}
       <div><label htmlFor="report" className="font-medium">Your report and implementation</label><p className="mt-1 text-xs text-ink-muted">Include calculations, commands, relevant code, measured results, failures and limitations. Cite recorded experiments where useful. Do not submit passwords, API keys or personal customer data.</p><textarea id="report" required minLength={200} maxLength={30000} rows={12} value={draft.report} onChange={e=>update('report',e.target.value)} className="mt-2 w-full rounded-lg border border-line p-3 text-sm"/></div>
       {!unlocked&&<p className="text-sm text-amber-800">Pass the preceding milestone before submitting this one. You can still read the brief and prepare a draft.</p>}
       {!baseline&&<p className="text-sm text-amber-800">Record the baseline check above before submitting your first milestone.</p>}
       {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
       <button disabled={busy||!unlocked||!baseline||draft.report.trim().length<200} className="rounded-lg bg-brand px-4 py-2 text-sm text-white disabled:opacity-40">{busy?'Saving…':'Submit for rubric assessment'}</button>
     </form>}
     {latest&&<div className="mt-6 border-t border-line pt-5"><h3 className="font-semibold">Latest saved submission</h3><pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify(latest.benchmark.metrics,null,2)}</pre><ul className="mt-3 space-y-1 text-sm">{Object.entries(latest.benchmark.checks).map(([key,value])=><li key={key} className={value?'text-emerald-700':'text-amber-800'}>{value?'✓':'Revisit:'} {key.replaceAll('_',' ')}</li>)}</ul>{latest.assessment&&<AssessmentFeedback job={latest.assessment} onChange={changed}/>}</div>}
     {item.experiments.length>0&&<details className="mt-6"><summary className="cursor-pointer text-sm text-brand">Recorded development experiments ({item.experiments.length})</summary>{item.experiments.map(e=><div key={e.id} className="mt-3 rounded-lg border border-line p-3"><p className="text-xs">Run {e.id} · {e.created_at}</p><pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify({configuration:e.artifact,result:e.benchmark},null,2)}</pre></div>)}</details>}
     {item.submissions.length>1&&<details className="mt-6"><summary className="cursor-pointer text-sm text-brand">Earlier saved revisions</summary>{item.submissions.slice(1).map(work=><div key={work.id} className="mt-3 rounded-lg border border-line p-3"><p className="text-xs">Submission {work.id} · {work.assessment?.status}</p><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs">{work.report}</pre></div>)}</details>}
   </section>
   {allPassed&&(project.evidence_check.transfer===null||showTransfer)&&<EvidenceCheck skill={project.skill} phase="transfer" onComplete={()=>{setShowTransfer(true);load().catch(()=>{});}}/>}
   {allPassed&&project.evidence_check.transfer!==null&&project.evidence_check.transfer<80&&<section className="mt-6 rounded-xl border border-amber-300 p-5"><h2 className="font-semibold">Close the remaining evidence gap</h2><p className="mt-2 text-sm">The original transfer score stays recorded. Use its feedback to revise the final project milestone. Once the revised work passes, a separate reassessment becomes available.</p><button onClick={()=>setRecheck(!recheck)} className="mt-3 text-sm text-brand underline">Open reassessment</button>{recheck&&<EvidenceCheck skill={project.skill} phase="reassessment" onComplete={()=>load().catch(()=>{})}/>}</section>}
   {project.evidence_check.retention_due&&<section className="mt-6 rounded-xl border border-line p-5"><h2 className="font-semibold">Check what you retain</h2><p className="mt-2 text-sm">Delayed check due: {new Date(project.evidence_check.retention_due+'Z').toLocaleDateString()}. A first success and durable recall are different outcomes.</p>{project.evidence_check.retention_available&&<EvidenceCheck skill={project.skill} phase="retention" onComplete={()=>load().catch(()=>{})}/>}</section>}
   <Link href="/dashboard/outcomes" className="mt-8 inline-block text-sm text-brand underline">See your learning evidence →</Link>
 </main>;
}
