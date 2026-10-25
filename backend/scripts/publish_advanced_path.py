"""Add advanced project-backed lessons, refusing unknown instructor edits."""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.db import Base, SessionLocal, engine
from app.models import Course, Module, Lesson
from app.models.course import FlashcardDeck
from app.models.learning import LearningUnit, LearningRevision
from app.services.learning import content_hash
from content.advanced.lessons import ADVANCED_UNITS


def publish(db):
    foundation=db.query(Course).filter_by(slug='ai-fundamentals').one()
    course=db.query(Course).filter_by(slug='advanced-ml-research').first()
    if not course:
        course=Course(slug='advanced-ml-research',title='Advanced ML and Research: Reproduce, Measure, Defend',
                      description='Six project-backed units covering training, generalization, experimental design, adaptation, multimodal evaluation and research reproduction. Includes code, datasets, rubric review and delayed transfer checks.',
                      category='Advanced AI',instructor_id=foundation.instructor_id,is_published=True)
        db.add(course);db.flush()
    course.is_published=True
    names=['Training and generalization','Experiments and adaptation','Multimodal evidence and research']
    changes=[]
    for index,spec in enumerate(ADVANCED_UNITS):
        chapter=db.query(Module).filter_by(course_id=course.id,title=names[index//2]).first()
        if not chapter:
            chapter=Module(course_id=course.id,title=names[index//2],objective='Produce reproducible evidence for the research project.',order_index=index//2+1)
            db.add(chapter);db.flush()
        lesson=db.query(Lesson).filter_by(slug=spec['slug']).first()
        if not lesson:
            lesson=Lesson(module_id=chapter.id,slug=spec['slug'],title=spec['title'],content_markdown='',content_blocks=[],order_index=index%2+1)
            db.add(lesson);db.flush()
        unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
        version=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
        if unit:
            if content_hash(lesson)!=unit.content_hash:raise ValueError('Unrecognized instructor edit: '+spec['slug'])
            if unit.version==version:continue
        elif lesson.content_markdown:raise ValueError('Unrecognized advanced lesson: '+spec['slug'])
        db.add(LearningRevision(lesson_id=lesson.id,version=unit.version if unit else 'before-advanced',
                 snapshot=dict(title=lesson.title,content_markdown=lesson.content_markdown,content_blocks=lesson.content_blocks,estimated_minutes=lesson.estimated_minutes)))
        blocks=[dict(type='text',markdown='## Your goal\n\n'+spec['objective']+'\n\n**Prerequisites:** '+spec['prerequisites'])]
        blocks += [dict(type='text',markdown='## '+title+'\n\n'+body) for title,body in spec['sections']]
        lesson.title,lesson.content_blocks=spec['title'],blocks
        lesson.content_markdown='\n\n'.join(b['markdown'] for b in blocks)
        lesson.estimated_minutes=spec['estimated_minutes']
        if not unit:
            unit=LearningUnit(lesson_id=lesson.id);db.add(unit)
        unit.version,unit.content_hash=version,content_hash(lesson)
        unit.objective,unit.prerequisites=spec['objective'],spec['prerequisites']
        unit.sources,unit.exercise=spec['sources'],spec['exercise']
        unit.stage,unit.position=spec['stage'],15+index
        unit.reviewed_on,unit.review_due=date(2026,10,25),date(2027,1,23)
        changes.append(spec['slug'])
    db.flush()
    return changes


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        changed=publish(db)
        if args.apply:db.commit()
        else:db.rollback()
        print(json.dumps(dict(applied=args.apply,changes=changed)))
