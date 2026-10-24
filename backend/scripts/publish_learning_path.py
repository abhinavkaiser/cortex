"""Transactional, idempotent curriculum publication. Dry-run unless --apply.

Existing reviewed or instructor-edited text must match a known hash. Original
content is snapshotted in learning_revisions; learners and attempts are retained.
Production deployment additionally makes a full consistent SQLite backup.
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.db import Base, SessionLocal, engine
from app.models import *  # noqa: F403
from app.models.course import FlashcardDeck
from app.models.learning import LearningRevision, LearningUnit, LearningQuizPublication
from app.services.learning import content_hash
from content.learning_path import REVIEWED_ON, REVIEW_DUE, UNITS
from content.learning_assessments import ASSESSMENTS

BASELINE = json.loads((Path(__file__).resolve().parents[1] / 'content/baseline_hashes.json').read_text())


def publish(db):
    foundation = db.query(Course).filter_by(slug="ai-fundamentals").one()
    bridge = db.query(Course).filter_by(slug="ai-technical-bridge").first()
    if bridge is None:
        bridge = Course(slug="ai-technical-bridge", title="AI Technical Bridge: From Concepts to Experiments",
                        description="Six hands-on units: Python and data, APIs, vectors, evaluation, training and a reproducible project. Includes a free, runnable lab pack.",
                        category="Technical foundations", instructor_id=foundation.instructor_id, is_published=True)
        db.add(bridge)
        db.flush()
    bridge.is_published = True
    module = db.query(Module).filter_by(course_id=bridge.id).first()
    if module is None:
        module = Module(course_id=bridge.id, title="Build, measure and explain", objective="Prepare for the AI Developer course with reproducible experiments.", order_index=0)
        db.add(module)
        db.flush()
    changes = []
    for position, spec in enumerate(UNITS):
        lesson = db.query(Lesson).filter_by(slug=spec['slug']).first()
        if lesson is None:
            if spec['course_slug'] != bridge.slug:
                raise ValueError('Expected foundation lesson missing: ' + spec['slug'])
            lesson = Lesson(module_id=module.id, slug=spec['slug'], title=spec['title'], content_markdown='', content_blocks=[], order_index=position)
            db.add(lesson)
            db.flush()
        elif not lesson.module or lesson.module.course.slug != spec['course_slug']:
            raise ValueError('Lesson belongs to a different course: ' + spec['slug'])
        unit = db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
        version = hashlib.sha256(json.dumps([REVIEWED_ON, REVIEW_DUE, spec], sort_keys=True).encode()).hexdigest()
        if unit and unit.version == version:
            if content_hash(lesson) != unit.content_hash:
                raise ValueError('Instructor changes detected: ' + spec['slug'])
            continue
        if lesson.content_markdown and content_hash(lesson) != (unit.content_hash if unit else BASELINE.get(spec['slug'])):
            raise ValueError('Unreviewed source content; publication aborted: ' + spec['slug'])
        db.add(LearningRevision(lesson_id=lesson.id, version=unit.version if unit else 'pre-interactive',
                               snapshot=dict(title=lesson.title, content_markdown=lesson.content_markdown,
                                             content_blocks=lesson.content_blocks, estimated_minutes=lesson.estimated_minutes)))
        lesson.title = spec['title']
        blocks = [dict(type='text', markdown='## Your goal\n\n' + spec['objective'] + '\n\n**Before you start:** ' + spec['prerequisites'])]
        blocks += [dict(type='text', markdown='## ' + title + '\n\n' + body) for title, body in spec['sections']]
        lesson.content_blocks = blocks
        lesson.content_markdown = '\n\n'.join(b['markdown'] for b in blocks)
        lesson.estimated_minutes = spec['estimated_minutes']
        if unit is None:
            unit = LearningUnit(lesson_id=lesson.id)
            db.add(unit)
        unit.version, unit.content_hash = version, content_hash(lesson)
        unit.objective, unit.prerequisites = spec['objective'], spec['prerequisites']
        unit.stage, unit.position = spec['stage'], position
        unit.sources, unit.exercise = spec['sources'], spec['exercise']
        unit.reviewed_on, unit.review_due = date.fromisoformat(REVIEWED_ON), date.fromisoformat(REVIEW_DUE)
        changes.append(spec['slug'])
    correction_specs = json.loads((Path(__file__).resolve().parents[1] / 'content/developer_corrections.json').read_text())
    for slug in dict.fromkeys(item['slug'] for item in correction_specs):
        lesson = db.query(Lesson).filter_by(slug=slug).one()
        edits = [item for item in correction_specs if item['slug'] == slug]
        version = 'correction-' + hashlib.sha256(json.dumps(edits, sort_keys=True).encode()).hexdigest()[:32]
        previous_correction = db.query(LearningRevision).filter_by(lesson_id=lesson.id, version=version).first()
        if previous_correction and content_hash(lesson) != BASELINE[slug]:
            from types import SimpleNamespace
            snapshot = json.loads(json.dumps(previous_correction.snapshot))
            for edit in edits:
                snapshot['content_markdown'] = snapshot['content_markdown'].replace(edit['old'], edit['new'])
                for block in snapshot['content_blocks']:
                    if 'markdown' in block:
                        block['markdown'] = block['markdown'].replace(edit['old'], edit['new'])
            expected = SimpleNamespace(**snapshot)
            if content_hash(lesson) == content_hash(expected):
                continue
            raise ValueError('Instructor changes detected after correction: ' + slug)
        if content_hash(lesson) != BASELINE[slug]:
            raise ValueError('Instructor changes detected in technical lesson: ' + slug)
        db.add(LearningRevision(lesson_id=lesson.id, version=version,
                               snapshot=dict(title=lesson.title, content_markdown=lesson.content_markdown,
                                             content_blocks=lesson.content_blocks, estimated_minutes=lesson.estimated_minutes)))
        blocks = json.loads(json.dumps(lesson.content_blocks))
        markdown = lesson.content_markdown
        for edit in edits:
            if edit['old'] not in markdown:
                raise ValueError('Expected correction text missing: ' + slug)
            markdown = markdown.replace(edit['old'], edit['new'])
            occurrences = 0
            for block in blocks:
                text = block.get('markdown', '')
                if edit['old'] in text:
                    block['markdown'] = text.replace(edit['old'], edit['new'])
                    occurrences += 1
            if not occurrences:
                raise ValueError('Rendered block correction text missing: ' + slug)
        lesson.content_blocks, lesson.content_markdown = blocks, markdown
        changes.append(slug)
    assessment_baselines = json.loads((Path(__file__).resolve().parents[1] / 'content/baseline_assessments.json').read_text())
    for spec in ASSESSMENTS:
        course = db.query(Course).filter_by(slug=spec['course']).one()
        chapter = db.query(Module).filter_by(course_id=course.id).order_by(Module.order_index).all()[spec['chapter']]
        quiz = db.query(Quiz).filter_by(module_id=chapter.id).first()
        deck = db.query(FlashcardDeck).filter_by(module_id=chapter.id).first()
        snapshot = dict(quiz={key: getattr(quiz, key) for key in ['title', 'passing_score', 'questions', 'randomize_questions', 'max_attempts']} if quiz else None,
                        deck=dict(title=deck.title, cards=deck.cards) if deck else None)
        publication = db.query(LearningQuizPublication).filter_by(quiz_id=quiz.id).first() if quiz else None
        target = hashlib.sha256(json.dumps([spec['questions'], 80], sort_keys=True).encode()).hexdigest()
        current = hashlib.sha256(json.dumps([quiz.questions, quiz.passing_score], sort_keys=True).encode()).hexdigest() if quiz else None
        if publication:
            if current != publication.version:
                raise ValueError('Instructor-edited assessment: ' + chapter.title)
            if target == current:
                continue
        elif spec['course'] == 'ai-fundamentals':
            if hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest() != assessment_baselines.get(chapter.title):
                raise ValueError('Unreviewed assessment source: ' + chapter.title)
        if quiz is None:
            quiz = Quiz(module_id=chapter.id, title=spec['title'])
            db.add(quiz)
            db.flush()
        if publication is None:
            publication = LearningQuizPublication(quiz_id=quiz.id, original=snapshot)
            db.add(publication)
        quiz.title, quiz.questions, quiz.passing_score = spec['title'], spec['questions'], 80
        quiz.randomize_questions, quiz.max_attempts = True, None
        publication.version = target
        if deck is None:
            deck = FlashcardDeck(module_id=chapter.id, title=spec['title'])
            db.add(deck)
        deck.title = spec['title'] + ' — review'
        deck.cards = [dict(front=front, back=back) for front, back in spec['cards']]
        changes.append('assessment:' + spec['course'] + ':' + str(spec['chapter']))
    db.flush()
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Additive tables only; no changes to existing columns or data here.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        changed = publish(db)
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(dict(applied=args.apply, changes=len(changed), slugs=changed)))
