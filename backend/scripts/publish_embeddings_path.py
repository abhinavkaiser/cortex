"""Add the embeddings/fine-tuning course; preserve learner data and instructor edits.

Dry-run unless --apply. Deployment backs up SQLite before invoking this publisher.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.db import Base,SessionLocal,engine
from app.models import Course,Module,Lesson
from app.models.learning import LearningUnit,LearningRevision
from app.services.learning import content_hash
from content.specializations.embeddings_finetuning import (UNITS,CHAPTERS,COURSE_SLUG,COURSE_TITLE,REVIEWED_ON,REVIEW_DUE)


def publish(db):
    foundation=db.query(Course).filter_by(slug='ai-fundamentals').one()
    course=db.query(Course).filter_by(slug=COURSE_SLUG).first()
    if course is None:
        course=Course(slug=COURSE_SLUG,title=COURSE_TITLE,
                      description='Fourteen lessons covering embeddings, vector search, embedding adaptation, instruction data, chat templates, SFT, LoRA, QLoRA, evaluation, DPO, distillation and deployment. Worked calculations, source references, decision feedback and assessed written reasoning. No GPU lab is required or claimed.',
                      category='AI engineering',instructor_id=foundation.instructor_id,is_published=True)
        db.add(course);db.flush()
    course.is_published=True
    chapters={}
    for index,title in enumerate(CHAPTERS):
        chapter=db.query(Module).filter_by(course_id=course.id,title=title).first()
        if chapter is None:
            chapter=Module(course_id=course.id,title=title,objective='Explain and defend an evidence-based engineering decision using the worked cases.',order_index=index)
            db.add(chapter);db.flush()
        chapters[index]=chapter
    changes=[]
    for index,spec in enumerate(UNITS):
        chapter=chapters[spec['chapter']]
        lesson=db.query(Lesson).filter_by(slug=spec['slug']).first()
        if lesson is None:
            lesson=Lesson(module_id=chapter.id,slug=spec['slug'],title=spec['title'],content_markdown='',content_blocks=[],order_index=index%2)
            db.add(lesson);db.flush()
        elif lesson.module_id!=chapter.id:
            raise ValueError('Lesson belongs to a different chapter: '+spec['slug'])
        unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
        version=hashlib.sha256(json.dumps([REVIEWED_ON,REVIEW_DUE,spec],sort_keys=True).encode()).hexdigest()
        if unit is not None:
            if content_hash(lesson)!=unit.content_hash:raise ValueError('Instructor changes detected: '+spec['slug'])
            if unit.version==version:continue
        elif lesson.content_markdown:raise ValueError('Unrecognized source content: '+spec['slug'])
        db.add(LearningRevision(lesson_id=lesson.id,version=unit.version if unit else 'before-embeddings-course',
                               snapshot=dict(title=lesson.title,content_markdown=lesson.content_markdown,content_blocks=lesson.content_blocks,estimated_minutes=lesson.estimated_minutes)))
        blocks=[dict(type='text',markdown='## Your goal\n\n'+spec['objective']+'\n\n**Prerequisites:** '+spec['prerequisites'])]
        blocks += [dict(type='text',markdown='## '+heading+'\n\n'+body) for heading,body in spec['sections']]
        lesson.title=spec['title'];lesson.content_blocks=blocks
        lesson.content_markdown='\n\n'.join(block['markdown'] for block in blocks)
        lesson.estimated_minutes=spec['estimated_minutes']
        if unit is None:unit=LearningUnit(lesson_id=lesson.id);db.add(unit)
        unit.version=version;unit.content_hash=content_hash(lesson)
        unit.objective=spec['objective'];unit.prerequisites=spec['prerequisites']
        unit.sources=spec['sources'];unit.exercise=spec['exercise'];unit.stage=spec['stage'];unit.position=21+index
        unit.reviewed_on=date.fromisoformat(REVIEWED_ON);unit.review_due=date.fromisoformat(REVIEW_DUE)
        changes.append(spec['slug'])
    db.flush()
    return changes


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        changes=publish(db)
        if args.apply:db.commit()
        else:db.rollback()
        print(json.dumps(dict(applied=args.apply,changes=changes)))
