"use client";
import {useEffect} from 'react';
import {studio} from '@/lib/studio';

export function LessonActivity({lessonId}:{lessonId:number}){
  useEffect(()=>{
    let lastInteraction=Date.now();
    const active=()=>{lastInteraction=Date.now();};
    const events=['pointerdown','keydown','scroll'];
    events.forEach(event=>window.addEventListener(event,active,{passive:true}));
    studio.activity(lessonId,0).catch(()=>{});
    const timer=setInterval(()=>{
      if(document.visibilityState==='visible'&&document.hasFocus()&&Date.now()-lastInteraction<60000)
        studio.activity(lessonId,20).catch(()=>{});
    },20000);
    return()=>{clearInterval(timer);events.forEach(event=>window.removeEventListener(event,active));};
  },[lessonId]);
  return null;
}
