"""Publication and learner-history contracts for the new specialization."""
import copy
from datetime import datetime
import pytest
from test_learning import setup
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.learning import LearningUnit,PracticeAttempt
from app.services.learning import content_hash
from content.specializations.embeddings_finetuning import UNITS,CHAPTERS,COURSE_SLUG
from scripts.publish_embeddings_path import publish


def test_new_course_is_additive_idempotent_and_serves_private_assessed_practice(setup):
    client,db,user,other,foundation,original,old_unit=setup
    foundation.slug='ai-fundamentals';db.commit()
    original_hash=content_hash(original);original_version=old_unit.version
    assert len(publish(db))==14;db.commit()
    assert publish(db)==[];db.commit()
    course=db.query(Course).filter_by(slug=COURSE_SLUG).one()
    chapters=db.query(Module).filter_by(course_id=course.id).order_by(Module.order_index).all()
    assert [m.title for m in chapters]==CHAPTERS
    lessons=db.query(Lesson).filter(Lesson.module_id.in_([m.id for m in chapters])).all()
    assert len(lessons)==14
    assert content_hash(original)==original_hash and old_unit.version==original_version
    path=client.get('/api/learning/path').json()
    new=[item for item in path if item['course_slug']==COURSE_SLUG]
    assert len(new)==14
    first=client.get(f"/api/learning/lessons/{new[0]['lesson_id']}").json()
    assert len(first['exercise']['questions'])==2 and first['sources'] and not first['mastered']
    assert all('correct_index' not in q for q in first['exercise']['questions'])
    assert client.post('/api/users/lessons/complete',json={'lesson_id':new[0]['lesson_id']}).status_code==409


def test_publisher_retains_old_attempts_and_refuses_instructor_changes(setup,monkeypatch):
    from scripts import publish_embeddings_path as publisher
    client,db,user,other,foundation,original,old_unit=setup
    foundation.slug='ai-fundamentals';db.commit();publish(db);db.commit()
    lesson=db.query(Lesson).filter_by(slug=UNITS[0]['slug']).one()
    unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).one();old_version=unit.version
    attempt=PracticeAttempt(user_id=user.id,lesson_id=lesson.id,version=old_version,answers=[0,0],reflection='Preserve my first explanation and its original version.',score=0,submitted_at=datetime.utcnow())
    db.add(attempt);db.commit();attempt_id=attempt.id
    revised=copy.deepcopy(UNITS);revised[0]['sections'].append(('Revision note','Keep the original run manifest with the new evaluation.'))
    monkeypatch.setattr(publisher,'UNITS',revised)
    assert publish(db)==[lesson.slug];db.commit()
    assert unit.version!=old_version and db.get(PracticeAttempt,attempt_id).version==old_version
    lesson.content_markdown+='\nInstructor-owned explanation.';db.commit();edited=lesson.content_markdown
    with pytest.raises(ValueError,match='Instructor changes'):publish(db)
    db.rollback();db.refresh(lesson)
    assert lesson.content_markdown==edited and db.get(PracticeAttempt,attempt_id).reflection.startswith('Preserve')
