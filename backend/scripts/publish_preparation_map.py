"""Publish audited prerequisite metadata without invalidating existing practice."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.db import Base,SessionLocal,engine
from app.models import Course,Lesson,Module
from app.models.learning import LearningUnit
from app.models.preparation import PreparationProfile
from app.services.preparation import require_ready,profile_hash
from content.preparation_map import COURSE_ENTRIES,LESSON_REQUIREMENTS,PATH_ORDER,entry


def publish(db):
    changes=0
    def save(field,owner_id,spec):
        nonlocal changes
        row=db.query(PreparationProfile).filter_by(**{field:owner_id}).first()
        if row and row.managed_version is None:return
        if row and row.managed_version!=profile_hash(row):raise ValueError('Unrecognized prerequisite metadata edit')
        if row is None:row=PreparationProfile(**{field:owner_id});db.add(row)
        old=row.managed_version
        for key,value in spec.items():setattr(row,key,value)
        row.managed_version=profile_hash(row)
        changes+=old!=row.managed_version
    courses=db.query(Course).filter_by(is_published=True).all()
    for course in courses:
        spec=COURSE_ENTRIES.get(course.slug)
        if spec:save('course_id',course.id,spec)
        elif not db.query(PreparationProfile).filter_by(course_id=course.id).first():raise ValueError('Published course needs declared preparation: '+course.slug)
        previous=None
        modules=db.query(Module).filter_by(course_id=course.id).order_by(Module.order_index,Module.id).all()
        for module in modules:
            for lesson in db.query(Lesson).filter_by(module_id=module.id).order_by(Lesson.order_index,Lesson.id).all():
                requires=LESSON_REQUIREMENTS.get(lesson.slug,[previous.slug] if previous else [])
                if requires:
                    targets=[db.query(Lesson).filter_by(slug=slug).one() for slug in requires]
                    text='Prepare with: '+'; '.join(l.title for l in targets)+'.'
                else:text='Start here'+(' after the linked course preparation.' if not spec or not spec['beginner'] else '. No earlier lesson is required.')
                save('lesson_id',lesson.id,entry(text,lessons=requires,beginner=not requires))
                previous=lesson
    for position,slug in enumerate(PATH_ORDER):
        lesson=db.query(Lesson).filter_by(slug=slug).one()
        unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).one()
        unit.position=position
    db.flush()
    result=require_ready(db)
    return dict(changed_profiles=changes,**result)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');args=p.parse_args();Base.metadata.create_all(engine)
    with SessionLocal() as db:
        result=publish(db)
        if args.apply:db.commit()
        else:db.rollback()
        print(json.dumps(dict(applied=args.apply,**result)))
