"""Schemas for the general-purpose course/chapter/quiz/certificate system
(see models/course.py). Kept in its own file, separate from schemas/user.py's
Track/Lesson schemas, since Course and Track are parallel systems sharing
the underlying Module/Lesson tables but not the same API surface."""

from datetime import datetime

from pydantic import BaseModel

# A single answer's value: an int (multiple_choice/true_false selected
# index), a list[int] (multi_select selected indices), a str (short_answer
# free text), or None (unanswered). Mirrors QuizAttempt.answers's shape --
# see that model's docstring.
AnswerValue = int | list[int] | str | None


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
    certificate_validity_days: int | None = None


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
    estimated_total_minutes: int  # sum of every lesson's estimated_minutes -- "how long is this course"
    certificate_validity_days: int | None

    enrolled: bool
    progress_pct: int | None  # None until enrolled
    completed_at: datetime | None


# ---- Chapters (Module) / Lessons --------------------------------------


class ChapterCreate(BaseModel):
    title: str
    objective: str = ""
    order_index: int = 0


class ChapterUpdate(BaseModel):
    """All fields optional -- PATCH semantics. Used both for editing an
    existing chapter's title/objective and for reordering (order_index)."""

    title: str | None = None
    objective: str | None = None
    order_index: int | None = None


class CourseLessonCreate(BaseModel):
    """Manually-authored lesson content for a course chapter -- plain
    content_markdown plus content_blocks (for the video/document/link block
    types -- see models/lesson.py) is enough here, no AI generation."""

    slug: str
    title: str
    content_markdown: str = ""
    content_blocks: list[dict] = []
    order_index: int = 0
    estimated_minutes: int = 10


class CourseLessonUpdate(BaseModel):
    """All fields optional -- PATCH semantics. Used both for editing an
    existing lesson's content and for reordering (order_index) within its
    chapter. Does not support moving a lesson to a different chapter --
    that's a bigger change (re-slugging, cross-chapter order_index
    renumbering) than "edit-after-create + reorder" needs to cover."""

    title: str | None = None
    content_markdown: str | None = None
    content_blocks: list[dict] | None = None
    order_index: int | None = None
    estimated_minutes: int | None = None


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
    at least once. randomize_questions/max_attempts are echoed back so the
    instructor editor can pre-fill them when replacing an existing quiz."""

    id: int
    title: str
    passing_score: int
    question_count: int
    best_score: int | None
    passed: bool
    randomize_questions: bool
    max_attempts: int | None


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
    certificate_validity_days: int | None
    estimated_total_minutes: int

    enrolled: bool
    progress_pct: int | None
    completed_at: datetime | None
    certificate_code: str | None  # set once the course is completed and a certificate exists

    chapters: list[ChapterOut]


# ---- Uploads (instructor course assets: PDFs, etc.) ------------------------


class UploadOut(BaseModel):
    """Response for POST /api/courses/{id}/upload -- the URL to reference
    in a lesson's content_blocks (a "document" block's url)."""

    url: str
    filename: str


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
    """One question in a POST .../quiz payload. type defaults to
    multiple_choice so existing authoring code that never set it keeps
    working unchanged. Fields not relevant to a given type are simply
    unused (e.g. correct_indices on a multiple_choice question) -- kept as
    one flat shape rather than a discriminated union so the instructor
    editor's form state doesn't need to reshape itself per type."""

    type: str = "multiple_choice"  # multiple_choice | multi_select | true_false | short_answer
    question: str
    choices: list[str] = []
    correct_index: int | None = None  # multiple_choice / true_false
    correct_indices: list[int] = []  # multi_select
    sample_answer: str = ""  # short_answer -- shown to the instructor grading it, not graded automatically


class QuizCreate(BaseModel):
    """POST .../quiz upserts -- if the chapter already has a Quiz row, its
    title/passing_score/questions/settings are replaced rather than a
    second Quiz being created (see models/course.py's Quiz docstring)."""

    title: str
    passing_score: int = 70
    questions: list[QuizQuestionCreate]
    randomize_questions: bool = False
    max_attempts: int | None = None


class QuizQuestionTakeOut(BaseModel):
    """A question as served to someone about to take the quiz --
    correct_index/correct_indices deliberately omitted; grading happens
    server-side on submit (see POST /api/quizzes/{id}/attempt).
    original_index is this question's position in the quiz's stored
    `questions` list -- when randomize_questions shuffles display order,
    the client echoes these back (as QuizAttemptRequest.question_order) so
    submit_attempt can grade each answer against the right question."""

    original_index: int
    type: str
    question: str
    choices: list[str]


class QuizTakeOut(BaseModel):
    id: int
    title: str
    passing_score: int
    max_attempts: int | None
    attempts_used: int  # this user's attempt count so far, for the UI to show "2 of 3 attempts used"
    questions: list[QuizQuestionTakeOut]


class QuizAttemptRequest(BaseModel):
    answers: list[AnswerValue]  # one per question, in the order the questions were presented
    question_order: list[int] | None = None  # original_index per answer, from QuizQuestionTakeOut -- required when the quiz was fetched randomized


class QuestionResult(BaseModel):
    type: str
    correct: bool | None  # None for a short_answer question -- not auto-gradable, pending instructor review
    selected: AnswerValue
    correct_index: int | None = None
    correct_indices: list[int] | None = None


class QuizAttemptResult(BaseModel):
    score: int  # provisional if status == "pending" -- computed over auto-gradable questions only
    passed: bool  # always False while status == "pending"
    status: str  # "graded" | "pending"
    passing_score: int
    results: list[QuestionResult]
    course_completed: bool  # True if this attempt just cleared the course's completion bar


class QuizAttemptOut(BaseModel):
    id: int
    score: int
    passed: bool
    status: str
    attempted_at: datetime


# ---- Instructor grading queue (short_answer questions) --------------------


class PendingAttemptOut(BaseModel):
    """One row in the instructor's grading queue (GET
    /api/quizzes/{id}/pending-attempts) -- everything needed to grade an
    attempt without a second round-trip: the learner's answers next to each
    question's text/type/sample_answer."""

    id: int
    user_id: int
    user_email: str
    user_full_name: str
    attempted_at: datetime
    questions: list[dict]  # [{"type","question","sample_answer"?}, ...] in the order answers[] corresponds to
    answers: list[AnswerValue]


class GradeAttemptRequest(BaseModel):
    """Instructor's final call on a pending attempt -- score/passed aren't
    recomputed from the answers (short_answer can't be auto-scored), the
    instructor supplies both directly."""

    score: int
    passed: bool


class GradeAttemptResult(BaseModel):
    id: int
    score: int
    passed: bool
    status: str
    course_completed: bool


# ---- Certificates ---------------------------------------------------------


class CertificateOut(BaseModel):
    id: int
    course_id: int
    course_title: str
    certificate_code: str
    issued_at: datetime
    expires_at: datetime | None
    is_expired: bool


class CertificateVerifyOut(BaseModel):
    """Public, no-auth response -- deliberately minimal (no email, no
    internal ids) since anyone with the code can view this."""

    learner_name: str
    course_title: str
    issued_at: datetime
    expires_at: datetime | None
    is_expired: bool


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
