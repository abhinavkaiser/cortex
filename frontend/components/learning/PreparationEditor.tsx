"use client";
import {useEffect,useState} from 'react';
import {request} from '@/lib/api';
import type {Preparation} from '@/lib/types';

type Options={courses:{slug:string;title:string}[];lessons:{slug:string;title:string;course_slug:string}[]};
export function PreparationEditor({courseId,courseSlug,preparation,onSaved}:{courseId:number;courseSlug:string;preparation?:Preparation|null;onSaved:()=>void}){
 const [statement,setStatement]=useState(preparation?.statement??'');const [beginner,setBeginner]=useState(preparation?.beginner??false);
 const [courses,setCourses]=useState<string[]>(preparation?.items.filter(i=>i.kind==='course').map(i=>i.slug)??[]);
 const [lessons,setLessons]=useState<string[]>(preparation?.items.filter(i=>i.kind==='lesson').map(i=>i.slug)??[]);
 const [options,setOptions]=useState<Options>({courses:[],lessons:[]});const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [saved,setSaved]=useState(false);
 useEffect(()=>{request<Options>(`/api/courses/${courseId}/prerequisites/options`).then(setOptions).catch(e=>setError(e.message));},[courseId]);
 async function save(){setBusy(true);setError('');setSaved(false);try{await request(`/api/courses/${courseId}/prerequisites`,{method:'PUT',body:JSON.stringify({statement,beginner,course_slugs:courses,lesson_slugs:lessons})});setSaved(true);onSaved();}catch(e){setError(e instanceof Error?e.message:'Preparation could not be saved.');}finally{setBusy(false);}}
 function start(value:boolean){setBeginner(value);if(value){setCourses([]);setLessons([]);if(!statement.trim())setStatement('Start here. No previous coursework is required.');}setSaved(false);}
 return <section className="mt-6 rounded-xl border border-line p-5"><h2 className="font-semibold">Course prerequisites</h2>
   <p className="mt-2 text-xs text-ink-muted">Declare a beginner entry or select the published preparation learners need. Publishing checks availability and circular dependencies.</p>
   <label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={beginner} onChange={e=>start(e.target.checked)}/>No previous coursework is required</label>
   <label className="mt-4 block text-sm">Preparation guidance<textarea aria-label="Preparation guidance" rows={3} value={statement} onChange={e=>{setStatement(e.target.value);setSaved(false);}} className="mt-2 w-full rounded-lg border border-line p-3"/></label>
   {!beginner&&<div className="mt-4 space-y-3">
     <label className="block text-sm">Add a prerequisite course<select aria-label="Add a prerequisite course" value="" onChange={e=>{if(e.target.value)setCourses(current=>[...current,e.target.value]);setSaved(false);}} className="mt-2 w-full rounded-lg border border-line p-2"><option value="">Choose a published course</option>{options.courses.filter(c=>!courses.includes(c.slug)).map(c=><option key={c.slug} value={c.slug}>{c.title}</option>)}</select></label>
     <label className="block text-sm">Add a prerequisite lesson<select aria-label="Add a prerequisite lesson" value="" onChange={e=>{if(e.target.value)setLessons(current=>[...current,e.target.value]);setSaved(false);}} className="mt-2 w-full rounded-lg border border-line p-2"><option value="">Choose a published lesson</option>{options.lessons.filter(l=>l.course_slug!==courseSlug&&!lessons.includes(l.slug)).map(l=><option key={l.slug} value={l.slug}>{l.title}</option>)}</select></label>
     <ul className="space-y-2 text-sm">{courses.map(slug=><li key={slug}>{options.courses.find(c=>c.slug===slug)?.title??preparation?.items.find(i=>i.slug===slug)?.title}<button type="button" onClick={()=>{setCourses(current=>current.filter(s=>s!==slug));setSaved(false);}} className="ml-3 text-brand underline">Remove</button></li>)}{lessons.map(slug=><li key={slug}>{options.lessons.find(l=>l.slug===slug)?.title??preparation?.items.find(i=>i.slug===slug)?.title}<button type="button" onClick={()=>{setLessons(current=>current.filter(s=>s!==slug));setSaved(false);}} className="ml-3 text-brand underline">Remove</button></li>)}</ul>
   </div>}
   {error&&<p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
   {saved&&<p className="mt-3 text-sm text-emerald-700">Preparation saved and checked.</p>}
   <button type="button" onClick={save} disabled={busy||statement.trim().length<15||!beginner&&courses.length+lessons.length===0} className="mt-4 rounded-lg border border-brand px-3 py-2 text-sm text-brand disabled:opacity-40">{busy?'Saving…':'Save prerequisites'}</button>
 </section>;
}
