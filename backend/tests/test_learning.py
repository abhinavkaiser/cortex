"""Learning contract tests, isolated from development and production databases."""
import copy
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Configure imports only. Every request overrides DB access below.
os.environ['DATABASE_URL'] = 'sqlite://'
from app.core.db import Base, get_db
from app.api.deps import get_current_user
from app.main import app
from app.models import Course, Lesson, Module, User, UserRole
from app.models.learning import LearningUnit, PracticeAttempt, CurriculumSignal
from app.models.daily_pulse import DailyPulse, PulseStatus
from app.models.track import Track
from app.services.learning import content_hash
from app.services.curriculum_updates import ingest
from content.learning_path import UNITS
from scripts.publish_learning_path import publish


@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    user = User(email='one@example.com', hashed_password='unused', full_name='One')
    other = User(email='two@example.com', hashed_password='unused', full_name='Two')
    db.add_all([user, other]); db.flush()
    course = Course(slug='test', title='Test', instructor_id=user.id, is_published=True)
    db.add(course); db.flush()
    module = Module(course_id=course.id, title='Test')
    db.add(module); db.flush()
    lesson = Lesson(module_id=module.id, slug='test', title='Test', content_markdown='Reviewed text', content_blocks=[])
    db.add(lesson); db.flush()
    unit = LearningUnit(lesson_id=lesson.id, version='v1', content_hash=content_hash(lesson),
                        objective='Explain a decision', prerequisites='None', sources=[],
                        reviewed_on=date.today(), review_due=date.today()+timedelta(days=30), position=0,
                        stage='AI foundation', exercise=copy.deepcopy(UNITS[0]['exercise']))
    db.add(unit); db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    # No lifespan: do not touch the module-global application engine.
    client = TestClient(app)
    yield client, db, user, other, course, lesson, unit
    app.dependency_overrides.clear()
    db.close(); engine.dispose()


def submission(unit, *, wrong=False):
    answers = [(q['correct_index'] + (1 if wrong else 0)) % 4 for q in unit.exercise['questions']]
    return dict(version=unit.version, answers=answers, reflection='I used the supplied evidence, selected a bounded action and checked the stated conditions.')


def test_answer_keys_hidden_and_incorrect_work_cannot_complete(setup):
    client, db, user, other, course, lesson, unit = setup
    detail = client.get(f'/api/learning/lessons/{lesson.id}').json()
    assert 'correct_index' not in json.dumps(detail)
    assert 'reference' not in detail['exercise']
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409
    result = client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit, wrong=True))
    assert result.status_code == 200 and result.json()['score'] == 0
    assert all(not item['correct'] for item in result.json()['feedback'])
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409


def test_revision_persists_and_is_private(setup):
    client, db, user, other, course, lesson, unit = setup
    client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit, wrong=True))
    result = client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit)).json()
    assert result['score'] == 100 and not result['practice_complete']
    assert result['assessment']['status'] == 'queued'
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409
    from app.services.education_worker import run_one
    factory = sessionmaker(bind=db.get_bind())
    def assessed(payload):
        return dict(status='graded',passed=all(payload['benchmark']['checks'].values()),score=100)
    run_one(factory,assessor=assessed,require_calibration=False)
    run_one(factory,assessor=assessed,require_calibration=False)
    db.expire_all()
    detail = client.get(f'/api/learning/lessons/{lesson.id}').json()
    assert detail['best_score'] == 100 and detail['latest_attempt']['reflection']
    assert db.query(PracticeAttempt).count() == 2
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 200
    app.dependency_overrides[get_current_user] = lambda: other
    assert client.get(f'/api/learning/lessons/{lesson.id}').json()['latest_attempt'] is None
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409


def test_current_version_required_even_after_an_old_pass(setup):
    client, db, user, other, course, lesson, unit = setup
    client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit))
    stale = submission(unit)
    unit.version = 'v2'; db.commit()
    assert client.get(f'/api/learning/lessons/{lesson.id}').json()['best_score'] is None
    assert client.post(f'/api/learning/lessons/{lesson.id}/practice', json=stale).status_code == 409
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409


def test_instructor_edit_invalidates_review_and_practice(setup):
    client, db, user, other, course, lesson, unit = setup
    client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit))
    lesson.content_markdown = 'Unreviewed replacement'; db.commit()
    assert client.get(f'/api/learning/lessons/{lesson.id}').json()['status'] == 'changed_since_review'
    assert client.post(f'/api/learning/lessons/{lesson.id}/practice', json=submission(unit)).status_code == 409
    assert client.post('/api/users/lessons/complete', json={'lesson_id': lesson.id}).status_code == 409


@pytest.mark.parametrize('field,value', [('answers', [-1, 99]), ('answers', [True, 0]), ('answers', [0]), ('reflection', ' '*50)])
def test_invalid_work_rejected(setup, field, value):
    client, db, user, other, course, lesson, unit = setup
    body = submission(unit); body[field] = value
    assert client.post(f'/api/learning/lessons/{lesson.id}/practice', json=body).status_code == 422
    assert db.query(PracticeAttempt).count() == 0


def test_draft_lessons_not_exposed_to_other_students(setup):
    client, db, user, other, course, lesson, unit = setup
    course.is_published = False; db.commit()
    app.dependency_overrides[get_current_user] = lambda: other
    for path in [f'/api/lessons/{lesson.id}', f'/api/learning/lessons/{lesson.id}', f'/api/learning/lessons/{lesson.id}/updates']:
        assert client.get(path).status_code == 404
    assert client.get('/api/learning/path').json() == []


def test_pack_contains_runnable_materials_only(setup):
    import io, zipfile
    client, *_ = setup
    response = client.get('/api/learning/lab-pack')
    assert response.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert 'cortex-labs/test_labs.py' in names
    assert 'cortex-labs/documents.json' in names
    assert not any('.env' in name or '__pycache__' in name for name in names)


def test_old_pulse_keeps_its_date_and_flagged_pulse_stays_hidden(setup):
    client, db, *_ = setup
    track = Track(slug='developer', name='Developer', description='')
    db.add(track); db.flush()
    for status, day in [(PulseStatus.PUBLISHED, date.today()-timedelta(days=2)), (PulseStatus.FLAGGED, date.today())]:
        db.add(DailyPulse(track_id=track.id, pulse_date=day, status=status, summary='Source summary',
                          sandbox_exercise='Try', quiz_question='Why?', quiz_choices=['A','B'], quiz_correct_index=0,
                          source_urls=[], generation_model='test'))
    db.commit()
    result = client.get('/api/daily-pulse/today').json()
    assert len(result) == 1 and result[0]['is_latest_from_earlier_day']
    assert result[0]['pulse_date'] == (date.today()-timedelta(days=2)).isoformat()


def test_source_updates_filter_dates_deduplicate_and_map_to_lessons(setup):
    import httpx
    client, db, *_ = setup
    now = datetime(2026, 10, 25, 12)
    xml = '''<rss version="2.0"><channel><title>Test</title>
    <item><title>Retrieval benchmark</title><link>https://example.org/new</link><pubDate>Sun, 25 Oct 2026 08:00:00 GMT</pubDate><description>Embedding evaluation</description></item>
    <item><title>Old retrieval</title><link>https://example.org/old</link><pubDate>Mon, 01 Jun 2026 08:00:00 GMT</pubDate></item>
    <item><title>Future retrieval</title><link>https://example.org/future</link><pubDate>Mon, 26 Oct 2026 08:00:00 GMT</pubDate></item>
    <item><title>Undated retrieval</title><link>https://example.org/undated</link></item>
    </channel></rss>'''
    def fetch(url):
        return httpx.Response(200, content=xml.encode(), request=httpx.Request('GET', url))
    feeds = [('Test', 'https://example.org/feed')]
    assert ingest(db, now=now, feeds=feeds, fetch=fetch)['added'] == 1
    assert ingest(db, now=now, feeds=feeds, fetch=fetch)['added'] == 0
    signal = db.query(CurriculumSignal).one()
    assert 'bridge-vectors-and-retrieval' in signal.lesson_slugs


def test_auth_required_for_practice():
    assert TestClient(app).get('/api/learning/path').status_code in [401, 403]


def test_authored_question_baselines_and_structure():
    assert len(UNITS) == 15
    questions = [q for unit in UNITS for q in unit['exercise']['questions']]
    longest = sum(max(range(4), key=lambda i: len(q['choices'][i])) == q['correct_index'] for q in questions)
    assert longest / len(questions) <= .5
    for unit in UNITS:
        assert len(unit['sections']) >= 5 and unit['sources']
        assert unit['exercise']['reference'] and len(unit['exercise']['rubric']) >= 3
        for q in unit['exercise']['questions']:
            assert len(set(q['choices'])) == 4
            assert len(q['feedback']) == 4


def test_revised_quiz_requires_current_version_and_does_not_reuse_old_pass(setup):
    from app.models.course import Quiz, QuizAttempt
    from app.models.learning import LearningQuizPublication
    from app.services import learning_quizzes
    from app.services.course_progress import quizzes_all_passed
    client, db, user, other, course, lesson, unit = setup
    quiz = Quiz(module_id=lesson.module_id, title='Revised quiz', passing_score=80,
                questions=[dict(type='multiple_choice', question='Which?', choices=['A', 'B'], correct_index=1, explanation='Evidence supports B.')])
    db.add(quiz); db.flush()
    db.add(QuizAttempt(user_id=user.id, quiz_id=quiz.id, answers=[0], score=100, passed=True, status='graded'))
    db.add(LearningQuizPublication(quiz_id=quiz.id, version='new', original={}))
    db.commit()
    assert not quizzes_all_passed(db, user.id, course.id)
    assert learning_quizzes.attempts(db, user.id, quiz).count() == 0
    take = client.get(f'/api/quizzes/{quiz.id}').json()
    assert take['version'] and 'correct_index' not in json.dumps(take)
    assert client.post(f'/api/quizzes/{quiz.id}/attempt', json=dict(answers=[1])).status_code == 409
    result = client.post(f'/api/quizzes/{quiz.id}/attempt', json=dict(answers=[1], version=take['version']))
    assert result.status_code == 200 and result.json()['passed']
    assert result.json()['results'][0]['explanation'] == 'Evidence supports B.'
    assert quizzes_all_passed(db, user.id, course.id)
    quiz.questions = [dict(type='multiple_choice', question='New case?', choices=['A', 'B'], correct_index=0)]
    db.commit()
    assert not quizzes_all_passed(db, user.id, course.id)
    assert client.post(f'/api/quizzes/{quiz.id}/attempt', json=dict(answers=[1], version=take['version'])).status_code == 409


def test_reviewed_assessment_baselines():
    from content.learning_assessments import ASSESSMENTS
    questions = [q for spec in ASSESSMENTS for q in spec['questions']]
    assert len(questions) == 15
    assert sum(max(range(4), key=lambda i: len(q['choices'][i])) == q['correct_index'] for q in questions) / len(questions) <= .5
    assert all(q['explanation'] for q in questions)


def test_worked_python_examples_execute(capsys):
    import re
    expected = ['30 3 0.1', 'False', "['refund', 'mixed', 'shipping']", '4.0 1.8 0.16']
    code_blocks = [code for unit in UNITS for _, body in unit['sections'] for code in re.findall(r'```python\n(.*?)```', body, re.S)]
    assert len(code_blocks) == len(expected)
    for code, output in zip(code_blocks, expected):
        exec(compile(code, '<course-example>', 'exec'), {})
        assert capsys.readouterr().out.strip() == output
