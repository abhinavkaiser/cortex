# Published prerequisite coverage

Add three beginner preparation courses: Python and Software Foundations for AI
(eight lessons), Mathematics for AI: From Arithmetic to Gradients (eight), and
Probability, Statistics and Experiments for AI (six). Their 22 lessons include
worked examples, 44 decision checks with feedback and assessed written exercises.
They supply the missing programming, algebra/logarithm/matrix/gradient and
probability/likelihood/uncertainty/experiment background.

The guided path grows from 35 to 57 units. Nontechnical role courses link to focused
preparation without requiring programming; technical courses use the full bridge
route. Every published course and lesson receives a PreparationProfile: 12 courses
and 122 lessons in the audited catalog. Course, lesson and project pages link to
published preparation. These links describe availability, not a learner’s mastery;
experienced learners can still open the content directly.

The research paper lesson requires experimental-design and multimodal lessons,
not the project milestone that itself requires the paper lesson. Metadata and
served introductory text use the corrected dependencies. Canonical lesson hashes,
practice versions, attempts and published amendments stay intact. The instructor
editor reads a protected canonical-source endpoint, preventing rendered metadata
or automatic additions from being saved into base teaching accidentally. Grading
and new update contexts use the resolved prerequisite text.

The dependency audit includes course completion, entry requirements and lesson
dependencies, detecting direct and mixed course/lesson cycles. Targets must be
published and contain teaching. Instructors declare a beginner entry or choose
published prerequisites before publishing. Missing targets, cycles, hiding required
resources and publishing empty lessons are rejected with transaction rollback.
Owner/admin permissions protect metadata editing and canonical reads. Instructor-
owned prerequisite metadata survives managed republication.

Deployment validates and runs publish_preparation_courses.py followed by
publish_preparation_map.py after the existing teaching publishers. Both are dry-run
by default. Changes use additive tables, preserve learner data and hide new courses
on rollback without deleting records. Prerequisites are separate from assessment
versioning so a wording/link repair does not revoke earned work.

Validation: 59 backend tests, optimized frontend build, full-catalog dependency
checks and disposable-copy dry-run/publication/idempotence/rollback/redeployment
checks pass. Tests cover unavailable targets, cycles, publishing/unpublishing,
permissions, source/assessment/amendment preservation and instructor overrides.
Browser evidence is retained in workspace reports. No GPU lab or executed model-
training outcome is claimed by these preparation courses.
