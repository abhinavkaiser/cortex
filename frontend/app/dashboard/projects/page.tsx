"use client";
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {studio,type ProjectSummary,type StudioStatus} from '@/lib/studio';

export default function ProjectsPage(){
 const [projects,setProjects]=useState<ProjectSummary[]>([]);const [status,setStatus]=useState<StudioStatus|null>(null);const [error,setError]=useState('');
 useEffect(()=>{Promise.all([studio.projects(),studio.status()]).then(([items,health])=>{setProjects(items);setStatus(health);}).catch(e=>setError(e.message));},[]);
 return <main className="mx-auto max-w-5xl px-6 py-12">
   <p className="text-xs font-semibold uppercase tracking-wide text-brand">Choose your specialization</p>
   <h1 className="mt-2 text-3xl font-semibold">Build something you can defend</h1>
   <p className="mt-3 max-w-3xl text-ink-muted">Each project provides a case, evidence, development experiments, three assessed milestones and a transfer check. Submit your reasoning and implementation, inspect specific feedback and revise until you meet the rubric.</p>
   <p className="mt-3 text-sm">New to AI? Start with the <Link href="/dashboard/learn" className="text-brand underline">AI foundation</Link>, then follow the preparation links for your chosen project. Experienced learners can use the baseline check to identify gaps.</p>
   {error&&<p role="alert" className="mt-6 text-red-700">{error}</p>}
   {status&&(!status.worker_online||!status.grading_calibrated)&&<p className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">Assessment is currently paused or unavailable. You can prepare work and run development experiments. Submissions remain saved and cannot pass until verified grading completes.</p>}
   <div className="mt-8 grid gap-5 md:grid-cols-2">{projects.map(project=><article key={project.slug} className="rounded-2xl border border-line p-6">
     <p className="text-xs font-medium uppercase tracking-wide text-brand">{project.audience} · about {project.hours} hours</p>
     <h2 className="mt-2 text-xl font-semibold">{project.title}</h2><p className="mt-3 text-sm leading-relaxed text-ink-muted">{project.brief}</p>
     <p className="mt-4 text-sm">{project.milestones_passed}/{project.milestones_total} milestones passed{project.completed?' · Project and transfer requirements met':''}</p>
     <Link href={`/dashboard/projects/${project.slug}`} className="mt-4 inline-block rounded-lg bg-brand px-4 py-2 text-sm text-white">Open project →</Link>
   </article>)}</div>
   <p className="mt-8 text-sm text-ink-muted">Automated review uses two models and objective checks where available. Submitted source code is inspected, not run on the application server. Instructor review is available when you disagree.</p>
 </main>;
}
