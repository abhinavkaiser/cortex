"""General-purpose course catalog and authoring -- coexists with (does not
replace) the fixed 3-Track curriculum in tracks.py. A Course is a Module
("chapter") + Lesson container just like a Track, but arbitrary,
instructor-authored, and gated by is_published + enrollment rather than the
Common-Core gate. See models/course.py for the schema rationale."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Certificate, Course, Enrollment, Quiz, QuizAttempt
from app.models.lesson import Lesson, UserLessonProgress
from app.models.module import Module
from app.models.user import User, UserRole
from app.schemas.course import (
    ChapterCreate,
    ChapterOut,
    CourseCreate,
    CourseDetailOut,
    CourseLessonCreate,
    CourseLessonOut,
    CourseSummary,
    CourseUpdate,
    EnrollRequest,
    QuizCreate,
    QuizSummaryOut,
    RosterRowOut,
)
from app.services.course_progress import course_progress_pct

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _require_instructor_or_admin(user: User) -> None:
    if user.role not in (UserRole.INSTRUCTOR, UserRole.ADMIN):
        raise HTTPException(403, "Instructor or admin role required")


def _require_owner_or_admin(course: Course, user: User) -> None:
    if course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(403, "Only the owning instructor or an admin can do this")


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return course


@router.get("", response_model=list[CourseSummary])
def list_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Catalog: learners see published courses only; an instructor/admin
    also sees their own unpublished (draft) courses mixed in."""
    courses = db.query(Course).order_by(Course.created_at.desc()).all()
    my_enrollments = {e.course_id: e for e in db.query(Enrollment).filter(Enrollment.user_id == user.id).all()}

    out = []
    for c in courses:
        visible = c.is_published or c.instructor_id == user.id or user.role == UserRole.ADMIN
        if not visible:
            continue
        enrollment = my_enrollments.get(c.id)
        out.append(
            CourseSummary(
                id=c.id,
                slug=c.slug,
                title=c.title,
                description=c.description,
                category=c.category,
                is_published=c.is_published,
                instructor_id=c.instructor_id,
                chapter_count=len(c.modules),
                lesson_count=sum(len(m.lessons) for m in c.modules),
                enrolled=enrollment is not None,
                progress_pct=course_progress_pct(db, user.id, c.id) if enrollment else None,
                completed_at=enrollment.completed_at if enrollment else None,
            )
        )
    return out


@router.post("", response_model=CourseSummary)
def create_course(body: CourseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_instructor_or_admin(user)
    if db.query(Course).filter(Course.slug == body.slug).first():
        raise HTTPException(409, f"Course slug '{body.slug}' already in use")

    course = Course(
        slug=body.slug,
        title=body.title,
        description=body.description,
        category=body.category,
        instructor_id=user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseSummary(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        category=course.category,
        is_published=course.is_published,
        instructor_id=course.instructor_id,
        chapter_count=0,
        lesson_count=0,
        enrolled=False,
        progress_pct=None,
        completed_at=None,
    )


@router.get("/{slug}", response_model=CourseDetailOut)
def get_course_detail(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.slug == slug).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if not course.is_published and course.instructor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(404, "Course not found")

    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id).first()

    completed_lesson_ids = {
        p.lesson_id for p in db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user.id).all()
    }

    chapters: list[ChapterOut] = []
    for m in course.modules:
        quiz_out = None
        if m.quiz:
            best = (
                db.query(QuizAttempt)
                .filter(QuizAttempt.user_id == user.id, QuizAttempt.quiz_id == m.quiz.id)
                .order_by(QuizAttempt.score.desc())
                .first()
            )
            quiz_out = QuizSummaryOut(
                id=m.quiz.id,
                title=m.quiz.title,
                passing_score=m.quiz.passing_score,
                question_count=len(m.quiz.questions or []),
                best_score=best.score if best else None,
                passed=best.passed if best else False,
            )
        chapters.append(
            ChapterOut(
                id=m.id,
                title=m.title,
                objective=m.objective,
                order_index=m.order_index,
                lessons=[
                    CourseLessonOut(
                        id=l.id,
                        title=l.title,
                        order_index=l.order_index,
                        estimated_minutes=l.estimated_minutes,
                        completed=l.id in completed_lesson_ids,
                    )
                    for l in m.lessons
                ],
                quiz=quiz_out,
            )
        )

    certificate_code = None
    if enrollment and enrollment.completed_at:
        cert = db.query(Certificate).filter(Certificate.user_id == user.id, Certificate.course_id == course.id).first()
        certificate_code = cert.certificate_code if cert else None

    return CourseDetailOut(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        category=course.category,
        is_published=course.is_published,
        instructor_id=course.instructor_id,
        enrolled=enrollment is not None,
        progress_pct=course_progress_pct(db, user.id, course.id) if enrollment else None,
        completed_at=enrollment.completed_at if enrollment else None,
        certificate_code=certificate_code,
        chapters=chapters,
    )


@router.patch("/{course_id}", response_model=CourseSummary)
def update_course(course_id: int, body: CourseUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course_or_404(db, course_id)
    _require_owner_or_admin(course, user)

    if body.title is not None:
        course.title = body.title
    if body.description is not None:
        course.description = body.description
    if body.category is not None:
        course.category = body.category
    if body.is_published is not None:
        course.is_published = body.is_published

    db.commit()
    db.refresh(course)
    return CourseSummary(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        category=course.category,
        is_published=course.is_published,
        instructor_id=course.instructor_id,
        chapter_count=len(course.modules),
        lesson_count=sum(len(m.lessons) for m in course.modules),
        enrolled=False,
        progress_pct=None,
        completed_at=None,
    )


@router.post("/{course_id}/chapters", response_model=ChapterOut)
def create_chapter(course_id: int, body: ChapterCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course_or_404(db, course_id)
    _require_owner_or_admin(course, user)

    module = Module(course_id=course.id, title=body.title, objective=body.objective, order_index=body.order_index)
    db.add(module)
    db.commit()
    db.refresh(module)
    return ChapterOut(id=module.id, title=module.title, objective=module.objective, order_index=module.order_index, lessons=[], quiz=None)


@router.post("/{course_id}/chapters/{module_id}/lessons", response_model=CourseLessonOut)
def create_course_lesson(
    course_id: int, module_id: int, body: CourseLessonCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    course = _get_course_or_404(db, course_id)
    _require_owner_or_admin(course, user)

    module = db.get(Module, module_id)
    if not module or module.course_id != course.id:
        raise HTTPException(404, "Chapter not found in this course")

    if db.query(Lesson).filter(Lesson.slug == body.slug).first():
        raise HTTPException(409, f"Lesson slug '{body.slug}' already in use")

    lesson = Lesson(
        module_id=module.id,
        slug=body.slug,
        title=body.title,
        content_markdown=body.content_markdown,
        order_index=body.order_index,
        estimated_minutes=body.estimated_minutes,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return CourseLessonOut(id=lesson.id, title=lesson.title, order_index=lesson.order_index, estimated_minutes=lesson.estimated_minutes, completed=False)


@router.post("/{course_id}/chapters/{module_id}/quiz", response_model=QuizSummaryOut)
def upsert_chapter_quiz(
    course_id: int, module_id: int, body: QuizCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    course = _get_course_or_404(db, course_id)
    _require_owner_or_admin(course, user)

    module = db.get(Module, module_id)
    if not module or module.course_id != course.id:
        raise HTTPException(404, "Chapter not found in this course")

    questions = [{"question": q.question, "choices": q.choices, "correct_index": q.correct_index} for q in body.questions]

    quiz = db.query(Quiz).filter(Quiz.module_id == module.id).first()
    if quiz:
        quiz.title = body.title
        quiz.passing_score = body.passing_score
        quiz.questions = questions
    else:
        quiz = Quiz(module_id=module.id, title=body.title, passing_score=body.passing_score, questions=questions)
        db.add(quiz)

    db.commit()
    db.refresh(quiz)
    return QuizSummaryOut(
        id=quiz.id, title=quiz.title, passing_score=quiz.passing_score, question_count=len(quiz.questions), best_score=None, passed=False
    )


@router.post("/{course_id}/enroll")
def enroll(course_id: int, body: EnrollRequest = EnrollRequest(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Self-enroll -- any authenticated user, idempotent. Re-enrolling
    (calling this again while already enrolled) is a no-op, not an error,
    since the frontend's "Enroll" button doesn't need to know whether this
    is the first call."""
    course = _get_course_or_404(db, course_id)
    existing = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id).first()
    if existing:
        return {"ok": True, "already_enrolled": True}

    db.add(Enrollment(user_id=user.id, course_id=course.id, due_at=body.due_at))
    db.commit()
    return {"ok": True, "already_enrolled": False}


@router.delete("/{course_id}/enroll")
def unenroll(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id).first()
    if enrollment:
        db.delete(enrollment)
        db.commit()
    return {"ok": True}


@router.get("/{course_id}/roster", response_model=list[RosterRowOut])
def get_roster(course_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _get_course_or_404(db, course_id)
    _require_owner_or_admin(course, user)

    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course.id).order_by(Enrollment.enrolled_at).all()
    return [
        RosterRowOut(
            user_id=e.user_id,
            email=e.user.email,
            full_name=e.user.full_name,
            enrolled_at=e.enrolled_at,
            progress_pct=course_progress_pct(db, e.user_id, course.id),
            completed_at=e.completed_at,
        )
        for e in enrollments
    ]
