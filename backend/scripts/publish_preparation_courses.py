"""Add beginner prerequisite teaching without changing existing lesson versions."""
import hashlib,json,sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.db import Base,SessionLocal,engine
from app.models import Course,Module,Lesson
from app.models.learning import LearningUnit,LearningRevision
from app.services.learning import content_hash
from content.foundations.prerequisites import UNITS,COURSES,REVIEWED_ON,REVIEW_DUE

CHAPTERS={
 'python-for-ai':['First programs and values','Collections and functions','Debugging and structured files','Environments and API contracts'],
 'mathematics-for-ai':['Numbers, rates and functions','Exponents and vector geometry','Matrices and derivatives','Gradients and optimization'],
 'probability-statistics-for-ai':['Probability and distributions','Sampling and causal experiments','Likelihood and paired evidence'],
}


def publish(db):
    owner=db.query(Course).filter_by(slug='ai-fundamentals').one().instructor_id
    changes=[]
    for slug,meta in COURSES.items():
        course=db.query(Course).filter_by(slug=slug).first()
        if course is None:
            course=Course(slug=slug,title=meta['title'],description=meta['description'],category=meta['category'],instructor_id=owner,is_published=True)
            db.add(course);db.flush()
        course.is_published=True
        chapters={}
        for number,title in enumerate(CHAPTERS[slug]):
            chapter=db.query(Module).filter_by(course_id=course.id,title=title).first()
            if chapter is None:
                chapter=Module(course_id=course.id,title=title,objective='Work through the examples and explain the preparation skill accurately.',order_index=number)
                db.add(chapter);db.flush()
            chapters[number]=chapter
        specs=[u for u in UNITS if u['course_slug']==slug]
        for index,spec in enumerate(specs):
            chapter=chapters[spec['chapter']]
            lesson=db.query(Lesson).filter_by(slug=spec['slug']).first()
            if lesson is None:
                lesson=Lesson(module_id=chapter.id,slug=spec['slug'],title=spec['title'],content_markdown='',content_blocks=[],order_index=index%2)
                db.add(lesson);db.flush()
            elif lesson.module_id!=chapter.id:raise ValueError('Lesson belongs to another chapter: '+spec['slug'])
            unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
            version=hashlib.sha256(json.dumps([REVIEWED_ON,REVIEW_DUE,spec],sort_keys=True).encode()).hexdigest()
            if unit:
                if content_hash(lesson)!=unit.content_hash:raise ValueError('Instructor changes detected: '+spec['slug'])
                if unit.version==version:continue
            elif lesson.content_markdown:raise ValueError('Unknown preparation text: '+spec['slug'])
            db.add(LearningRevision(lesson_id=lesson.id,version=unit.version if unit else 'before-preparation',snapshot=dict(title=lesson.title,content_markdown=lesson.content_markdown,content_blocks=lesson.content_blocks,estimated_minutes=lesson.estimated_minutes)))
            blocks=[dict(type='text',markdown='## Your goal\n\n'+spec['objective']+'\n\n**Prerequisites:** '+spec['prerequisites'])]
            blocks += [dict(type='text',markdown='## '+title+'\n\n'+body) for title,body in spec['sections']]
            lesson.title=spec['title'];lesson.content_blocks=blocks;lesson.content_markdown='\n\n'.join(b['markdown'] for b in blocks);lesson.estimated_minutes=spec['estimated_minutes']
            if unit is None:unit=LearningUnit(lesson_id=lesson.id);db.add(unit)
            unit.version=version;unit.content_hash=content_hash(lesson);unit.objective=spec['objective'];unit.prerequisites=spec['prerequisites']
            unit.stage=spec['stage'];unit.position=9+UNITS.index(spec);unit.sources=spec['sources'];unit.exercise=spec['exercise']
            unit.reviewed_on=date.fromisoformat(REVIEWED_ON);unit.review_due=date.fromisoformat(REVIEW_DUE)
            changes.append(spec['slug'])
    db.flush();return changes


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');args=p.parse_args();Base.metadata.create_all(engine)
    with SessionLocal() as db:
        changes=publish(db)
        if args.apply:db.commit()
        else:db.rollback()
        print(json.dumps(dict(applied=args.apply,changes=changes)))
