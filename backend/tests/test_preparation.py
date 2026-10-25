"""Prerequisite availability, cycle and authoring protections."""
import copy
import pytest
from test_learning import setup
from app.models import Course,Module,Lesson
from app.models.learning import LearningUnit,PracticeAttempt
from app.models.preparation import PreparationProfile
from app.services.preparation import audit,require_ready,public_preparation
from app.services.learning import content_hash
from content.preparation_map import COURSE_ENTRIES,PATH_ORDER
from content.learning_path import UNITS as BASIC
from content.advanced.lessons import ADVANCED_UNITS
from content.specializations.embeddings_finetuning import UNITS as EMBEDDINGS
from scripts.publish_preparation_courses import publish as publish_courses
from scripts.publish_preparation_map import publish as publish_map


def ready_fixture(data):
    client,db,user,other,course,lesson,unit=data
    db.add(PreparationProfile(course_id=course.id,statement='Start here. No previous coursework is required.',beginner=True,course_slugs=[],lesson_slugs=[]))
    db.add(PreparationProfile(lesson_id=lesson.id,statement='Start with this first lesson.',beginner=True,course_slugs=[],lesson_slugs=[]));db.commit()
    return data


def add_course(db,user,slug):
    course=Course(slug=slug,title=slug,instructor_id=user.id,is_published=True);db.add(course);db.flush()
    chapter=Module(course_id=course.id,title='Teaching',order_index=0);db.add(chapter);db.flush()
    lesson=Lesson(module_id=chapter.id,slug=slug+'-lesson',title=slug+' lesson',content_markdown='Substantive example teaching text.',content_blocks=[]);db.add(lesson);db.flush()
    db.add(PreparationProfile(course_id=course.id,statement='Start here without previous coursework.',beginner=True,course_slugs=[],lesson_slugs=[]))
    db.add(PreparationProfile(lesson_id=lesson.id,statement='Start with this lesson.',beginner=True,course_slugs=[],lesson_slugs=[]));db.commit()
    return course,lesson


def complete_catalog(data):
    client,db,user,other,course,lesson,unit=data
    course.slug='ai-fundamentals';lesson.slug=BASIC[0]['slug'];lesson.title=BASIC[0]['title'];unit.content_hash=content_hash(lesson);db.commit()
    courses={'ai-fundamentals':course};chapters={'ai-fundamentals':lesson.module}
    for slug in COURSE_ENTRIES:
        if slug in ('python-for-ai','mathematics-for-ai','probability-statistics-for-ai','ai-fundamentals'):continue
        c=Course(slug=slug,title=slug,instructor_id=user.id,is_published=True);db.add(c);db.flush();courses[slug]=c
        chapter=Module(course_id=c.id,title='Teaching',order_index=0);db.add(chapter);db.flush();chapters[slug]=chapter
    for position,spec in enumerate([*BASIC,*ADVANCED_UNITS,*EMBEDDINGS]):
        if spec['slug']==lesson.slug:continue
        body='## Your goal\n\n**Prerequisites:** '+spec['prerequisites']+'\n\n'+spec['sections'][0][1]
        l=Lesson(module_id=chapters[spec['course_slug']].id,slug=spec['slug'],title=spec['title'],content_markdown=body,content_blocks=[dict(type='text',markdown=body)],order_index=position);db.add(l);db.flush()
        db.add(LearningUnit(lesson_id=l.id,version='version-'+str(position),content_hash=content_hash(l),objective=spec['objective'],prerequisites=spec['prerequisites'],sources=spec['sources'],reviewed_on=unit.reviewed_on,review_due=unit.review_due,stage=spec['stage'],position=position,exercise=copy.deepcopy(spec['exercise'])))
    for slug in ['ai-developer','ai-practitioner','ai-leader','prompt-engineering-for-teams','building-ai-powered-products']:
        l=Lesson(module_id=chapters[slug].id,slug=slug+'-legacy',title='Existing '+slug,content_markdown='Existing course teaching.',content_blocks=[]);db.add(l)
    db.commit();publish_courses(db);db.commit()
    return data


def test_every_course_and_lesson_has_acyclic_available_preparation_without_resetting_work(setup):
    client,db,user,other,course,lesson,unit=complete_catalog(setup)
    old_version=unit.version;old_hash=content_hash(lesson)
    attempt=PracticeAttempt(user_id=user.id,lesson_id=lesson.id,version=old_version,answers=[0,0],reflection='Keep this earlier learner explanation.',score=0);db.add(attempt);db.commit();attempt_id=attempt.id
    from datetime import datetime
    from app.models.learning import CurriculumSignal
    from app.services.education_queue import enqueue
    from app.services.education_worker import publish_amendment
    from app.services.education_curriculum import effective_unit
    from test_education import valid_amendment
    paper=db.query(Lesson).filter_by(slug='advanced-paper-reproduction').one()
    paper_unit=db.query(LearningUnit).filter_by(lesson_id=paper.id).one()
    signal=CurriculumSignal(url='https://huggingface.co/blog/example',title='Public research evidence',summary='Example',source='Test',published_at=datetime.utcnow(),lesson_slugs=[paper.slug]);db.add(signal);db.flush()
    job=enqueue(db,key='preserved-amendment',kind='curriculum',user_id=None,subject_id=paper.id,version=paper_unit.version,payload=dict(signal_id=signal.id,content_hash=content_hash(paper),url=signal.url))
    publish_amendment(db,job,dict(amendment=valid_amendment(),source_sha256='a'*64));db.commit()
    effective_before=effective_unit(db,paper_unit).version
    result=publish_map(db);db.commit()
    assert result['verified'] and result['courses']==12 and not result['cycles'] and not result['errors']
    assert len(PATH_ORDER)==57 and len(client.get('/api/learning/path').json())==57
    assert publish_map(db)['changed_profiles']==0
    assert unit.version==old_version and content_hash(lesson)==old_hash and db.get(PracticeAttempt,attempt_id).reflection.startswith('Keep')
    for c in db.query(Course).filter_by(is_published=True):assert public_preparation(db,course_id=c.id)['verified']
    paper=db.query(Lesson).filter_by(slug='advanced-paper-reproduction').one()
    paper_unit=db.query(LearningUnit).filter_by(lesson_id=paper.id).one();paper_version=paper_unit.version;raw=paper.content_markdown
    response=client.get(f'/api/lessons/{paper.id}').json()
    assert 'research project milestones' in raw and 'research project milestones' not in response['content_markdown']
    assert response['preparation']['items'] and paper_unit.version==paper_version
    assert effective_unit(db,paper_unit).version==effective_before and len(effective_unit(db,paper_unit).exercise['questions'])==3
    current=effective_unit(db,paper_unit)
    answer=client.post(f'/api/learning/lessons/{paper.id}/practice',json=dict(version=current.version,answers=[q['correct_index'] for q in current.exercise['questions']],reflection='I distinguish source claims, controlled measurements and the limits of this example.'))
    assert answer.status_code==200
    from app.models.education import EducationJob
    saved=db.query(EducationJob).filter_by(kind='practice',subject_id=answer.json()['id']).one()
    assert 'research project milestones' not in saved.payload['lesson_context']

    assert client.get(f'/api/courses/{paper.module.course_id}/lessons/{paper.id}/source').json()['content_markdown']==raw


def test_publish_requires_a_declared_available_preparation_profile(setup):
    client,db,user,other,course,lesson,unit=ready_fixture(setup)
    draft=Course(slug='new-draft',title='New draft',instructor_id=user.id,is_published=False);db.add(draft);db.commit()
    chapter=client.post(f'/api/courses/{draft.id}/chapters',json=dict(title='Start',order_index=0)).json()
    response=client.post(f"/api/courses/{draft.id}/chapters/{chapter['id']}/lessons",json=dict(slug='new-draft-intro',title='Intro',content_markdown='A worked introductory lesson.'))
    assert response.status_code==200
    assert client.patch(f'/api/courses/{draft.id}',json=dict(is_published=True)).status_code==409
    assert not db.get(Course,draft.id).is_published
    body=dict(statement='Start here. No previous coursework is required.',beginner=True,course_slugs=[],lesson_slugs=[])
    assert client.put(f'/api/courses/{draft.id}/prerequisites',json=body).status_code==200
    assert client.patch(f'/api/courses/{draft.id}',json=dict(is_published=True)).status_code==200
    assert audit(db)['verified']


def test_cycles_and_unpublishing_required_material_are_rejected_atomically(setup):
    client,db,user,other,course,lesson,unit=ready_fixture(setup)
    second,second_lesson=add_course(db,user,'second')
    body=dict(statement='Prepare with the second published course.',beginner=False,course_slugs=['second'],lesson_slugs=[])
    assert client.put(f'/api/courses/{course.id}/prerequisites',json=body).status_code==200
    reverse={**body,'course_slugs':[course.slug]}
    assert client.put(f'/api/courses/{second.id}/prerequisites',json=reverse).status_code==409
    assert db.query(PreparationProfile).filter_by(course_id=second.id).one().beginner
    assert client.patch(f'/api/courses/{second.id}',json=dict(is_published=False)).status_code==409
    assert db.get(Course,second.id).is_published and audit(db)['verified']
    missing={**body,'course_slugs':['not-published']}
    assert client.put(f'/api/courses/{course.id}/prerequisites',json=missing).status_code==409
    own_lesson={**body,'course_slugs':[],'lesson_slugs':[lesson.slug]}
    assert client.put(f'/api/courses/{course.id}/prerequisites',json=own_lesson).status_code==409


def test_lesson_cycles_cross_course_visibility_and_owner_permissions(setup):
    from app.main import app
    from app.api.deps import get_current_user
    client,db,user,other,course,lesson,unit=ready_fixture(setup)
    second,second_lesson=add_course(db,user,'second')
    body=dict(statement='Prepare with the other lesson.',beginner=False,course_slugs=[],lesson_slugs=[second_lesson.slug])
    assert client.put(f'/api/courses/{course.id}/lessons/{lesson.id}/prerequisites',json=body).status_code==200
    body['lesson_slugs']=[lesson.slug]
    assert client.put(f'/api/courses/{second.id}/lessons/{second_lesson.id}/prerequisites',json=body).status_code==409
    assert audit(db)['verified']
    app.dependency_overrides[get_current_user]=lambda:other
    assert client.put(f'/api/courses/{course.id}/prerequisites',json=body).status_code==403
    assert client.get(f'/api/courses/{course.id}/prerequisites/options').status_code==403
    assert client.get(f'/api/courses/{course.id}/lessons/{lesson.id}/source').status_code==403
    app.dependency_overrides[get_current_user]=lambda:user


def test_empty_published_lessons_are_not_allowed(setup):
    client,db,user,other,course,lesson,unit=ready_fixture(setup)
    response=client.post(f'/api/courses/{course.id}/chapters/{lesson.module_id}/lessons',json=dict(slug='empty',title='Empty'))
    assert response.status_code==409 and not db.query(Lesson).filter_by(slug='empty').first()
    response=client.patch(f'/api/courses/{course.id}/chapters/{lesson.module_id}/lessons/{lesson.id}',json=dict(content_markdown='',content_blocks=[]))
    assert response.status_code==409 and db.get(Lesson,lesson.id).content_markdown



def test_instructor_preparation_changes_survive_republication(setup):
    client,db,user,other,course,lesson,unit=complete_catalog(setup)
    publish_map(db);db.commit()
    statement='Start here. This instructor-owned entry needs no previous coursework.'
    response=client.put(f'/api/courses/{course.id}/prerequisites',json=dict(statement=statement,beginner=True,course_slugs=[],lesson_slugs=[]))
    assert response.status_code==200
    publish_map(db);db.commit()
    row=db.query(PreparationProfile).filter_by(course_id=course.id).one()
    assert row.statement==statement and row.managed_version is None and audit(db)['verified']
