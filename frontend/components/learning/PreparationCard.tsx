import Link from 'next/link';
import type {Preparation} from '@/lib/types';

export function PreparationCard({preparation}:{preparation?:Preparation|null}){
 if(!preparation)return null;
 return <section className="mt-6 rounded-xl border border-brand/30 bg-surface p-5">
   <h2 className="font-semibold">Before you begin</h2>
   <p className="mt-2 text-sm leading-relaxed">{preparation.statement}</p>
   {preparation.items.length>0&&<details className="mt-3" open={preparation.items.length<=4}>
     <summary className="cursor-pointer text-sm font-medium text-brand">Preparation links ({preparation.items.length})</summary>
     <p className="mt-2 text-xs text-ink-muted">Use these courses and lessons to learn or refresh the background. Follow their preparation links if you need an earlier starting point.</p>
     <ul className="mt-3 space-y-2">{preparation.items.map(item=><li key={`${item.kind}:${item.slug}`} className="text-sm"><span className="mr-2 text-xs text-ink-muted">{item.kind==='course'?'Course':'Lesson'}</span><Link href={item.url} className="text-brand underline">{item.title}</Link></li>)}</ul>
   </details>}
   <p className={`mt-3 text-xs ${preparation.verified?'text-ink-muted':'text-amber-800'}`}>{preparation.verified?'The prerequisite courses and lessons are published in Cortex.':'Some prerequisite information needs instructor review.'}</p>
 </section>;
}
