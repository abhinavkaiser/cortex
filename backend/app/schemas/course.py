"""Schemas for the general-purpose course/chapter/quiz/certificate system
(see models/course.py). Kept in its own file, separate from schemas/user.py's
Track/Lesson schemas, since Course and Track are parallel systems sharing
the underlying Module/Lesson tables but not the same API surface."""

from datetime import datetime

from pydantic import BaseModel


# ---- Courses ----------------------------------------------------------


class CourseCreate(BaseModel):
    slug: str
    title: str
    description: str = ""
    category: str = ""


class CourseUpdate(BaseModel):
    """All fields optional -- PATCH semantics, only supplied fields change."""

    title: str | None = None
    description: str | None = None
    category: str | None = None
    is_published: bool | None = None


class CourseSummary(BaseModel):
    """One row in the course catalog (GET /api/courses) -- enrollment
    status/progress are the requesting user's own, None if not enrolled."""

    id: int
    slug: str
    title: str
    description: str
    category: str
    is_published: bool
    instructor_id: int
    chapter_count: int
    lesson_count: int

    enrolled: bool
    progress_pct: int | None  # None until enrolled
    completed_at: datetime | None


# ---- Chapters (Module) / Lessons --------------------------------------


class ChapterCreate(BaseModel):
    title: str
    objective: str = ""
    order_index: int = 0


class CourseLessonCreate(BaseModel):
    """Manually-authored lesson content for a course chapter -- plain
    content_markdown is enough here (no AI generation, no content_blocks
    authoring UI in scope for instructor-authored courses)."""

    slug: str
    title: str
    content_markdown: str = ""
    order_index: int = 0
    estimated_minutes: int = 10


class CourseLessonOut(BaseModel):
    id: int
    title: str
    order_index: int
    estimated_minutes: int
    completed: bool


class QuizSummaryOut(BaseModel):
    """A chapter's quiz as seen from the course-detail view -- no
    correct_index (see QuizTakeOut for the same omission on the
    quiz-taking endpoint), plus the user's best attempt if they've taken it
    at least once."""

    id: int
    title: str
    passing_score: int
    question_count: int
    best_score: int | None
    passed: bool


class ChapterOut(BaseModel):
    id: int
    title: str
    objective: str
    order_index: int
    lessons: list[CourseLessonOut]
    quiz: QuizSummaryOut | None


class CourseDetailOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    category: str
    is_published: bool
    instructor_id: int

    enrolled: bool
    progress_pct: int | None
    completed_at: datetime | None
    certificate_code: str | None  # set once the course is completed and a certificate exists

    chapters: list[ChapterOut]


# ---- Enrollment / roster ------------------------------------------------


class EnrollRequest(BaseModel):
    due_at: datetime | None = None


class RosterRowOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    enrolled_at: datetime
    progress_pct: int
    completed_at: datetime | None


# ---- Quizzes -------------------------------------------------------------


class QuizQuestionCreate(BaseModel):
    question: str
    choices: list[str]
    correct_index: int


class QuizCreate(BaseModel):
    """POST .../quiz upserts -- if the chapter already has a Quiz row, its
    title/passing_score/questions are replaced rather than a second Quiz
    being created (see models/course.py's Quiz docstring)."""

    title: str
    passing_score: int = 70
    questions: list[QuizQuestionCreate]


class QuizQuestionTakeOut(BaseModel):
    """A question as served to someone about to take the quiz --
    correct_index deliberately omitted; grading happens server-side on
    submit (see POST /api/quizzes/{id}/attempt)."""

    question: str
    choices: list[str]


class QuizTakeOut(BaseModel):
    id: int
    title: str
    passing_score: int
    questions: list[QuizQuestionTakeOut]


class QuizAttemptRequest(BaseModel):
    answers: list[int]  # chosen choice index per question, in question order


class QuestionResult(BaseModel):
    correct: bool
    correct_index: int
    selected_index: int


class QuizAttemptResult(BaseModel):
    score: int
    passed: bool
    passing_score: int
    results: list[QuestionResult]
    course_completed: bool  # True if this attempt just cleared the course's completion bar


class QuizAttemptOut(BaseModel):
    id: int
    score: int
    passed: bool
    attempted_at: datetime


# ---- Certificates ---------------------------------------------------------


class CertificateOut(BaseModel):
    id: int
    course_id: int
    course_title: str
    certificate_code: str
    issued_at: datetime


class CertificateVerifyOut(BaseModel):
    """Public, no-auth response -- deliberately minimal (no email, no
    internal ids) since anyone with the code can view this."""

    learner_name: str
    course_title: str
    issued_at: datetime


# ---- Learner course dashboard (GET /api/users/{id}/courses) -------------


class UserCourseOut(BaseModel):
    course_id: int
    slug: str
    title: str
    category: str
    progress_pct: int
    enrolled_at: datetime
    due_at: datetime | None
    completed_at: datetime | None
