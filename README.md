# Cortex AI

Interactive AI training platform: role-based learning tracks (AI Leader /
AI Practitioner / AI Developer), a shared Common Core every user completes
first, a daily autonomous "Daily Pulse" micro-learning pipeline, an
in-browser Prompt Playground sandbox, and a general-purpose **Course**
system -- arbitrary instructor-authored courses (chapters, lessons,
quizzes, certificates) that coexists with, and reuses the same underlying
tables as, the fixed 3-Track curriculum. See "Courses vs. Tracks" below.

## Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **Database:** SQLite via SQLAlchemy (swapped in for the originally-specced
  Postgres -- see "Scoping notes" below for what that trades away)
- **AI:** Runs on a local **Claude subscription** via the `claude` CLI
  (`claude --print`) -- flat-rate, no billed API key to configure. Used for
  generation and evaluation (LLM-as-judge). Embeddings (semantic cache) run
  locally too, via `sentence-transformers` -- no API for those either.

## Directory structure

```
cortex-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entrypoint
│   │   ├── api/
│   │   │   ├── deps.py                # auth dependency (JWT -> current user)
│   │   │   └── routes/
│   │   │       ├── auth.py            # register / login
│   │   │       ├── users.py           # onboarding, lesson completion, progress, courses-enrolled-in
│   │   │       ├── daily_pulse.py     # today's pulse, quiz answer check
│   │   │       ├── sandbox.py         # prompt playground execution
│   │   │       ├── tracks.py          # open-catalog browsing of the 3 fixed Tracks
│   │   │       ├── explore.py         # hand-built interactive AI concept demos
│   │   │       ├── courses.py         # course catalog + instructor authoring (chapters/lessons/quiz) + enroll/roster
│   │   │       ├── quizzes.py         # quiz-taking: fetch (no answers), grade+submit, attempt history
│   │   │       └── certificates.py    # learner's own certificates + public no-auth verification
│   │   ├── models/                    # SQLAlchemy models (see Database schema)
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── agents/
│   │   │   ├── news_ingest.py         # RSS fetch, no LLM calls
│   │   │   ├── daily_pulse_agent.py   # ingest -> generate (per track) -> evaluate -> persist
│   │   │   ├── evals.py               # deterministic checks + LLM-as-judge scoring
│   │   │   └── mcp_tools.py           # exposes the above as MCP tools over stdio
│   │   ├── services/
│   │   │   ├── claude_client.py       # all real LLM/embedding calls go through here (claude CLI + local embeddings)
│   │   │   ├── cache.py               # semantic cache (cosine similarity over embeddings)
│   │   │   ├── token_cost.py          # token/cost estimation
│   │   │   └── course_progress.py     # shared course-completion/certificate-issuance logic (used by both the lesson-complete and quiz-attempt routes)
│   │   └── core/
│   │       ├── config.py, db.py, security.py
│   ├── alembic/                       # migrations (SQLite-safe: render_as_batch)
│   ├── scripts/
│   │   ├── seed.py                    # seeds the 3 tracks + starter lessons + 2 example courses with quizzes
│   │   └── run_daily_pulse.py         # cron entrypoint -- one pulse per track, daily
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # login/register
│   │   ├── onboarding/page.tsx        # track selection
│   │   ├── certificates/verify/[code]/page.tsx  # PUBLIC, no-auth certificate verification
│   │   └── dashboard/
│   │       ├── layout.tsx             # shared top nav (Tracks/Courses/Daily Pulse/Sandbox/Certificates, + Instructor when role-gated)
│   │       ├── common-core/page.tsx   # shared gate before track curriculum unlocks
│   │       ├── tracks/[slug]/page.tsx # track curriculum progress
│   │       ├── daily-pulse/page.tsx
│   │       ├── sandbox/page.tsx
│   │       ├── courses/page.tsx               # course catalog, enroll, progress
│   │       ├── courses/[slug]/page.tsx        # chapters/lessons/quiz for one course
│   │       ├── courses/[slug]/quiz/[quizId]/page.tsx  # quiz-taking UI
│   │       ├── certificates/page.tsx          # learner's own earned certificates
│   │       └── instructor/courses/            # instructor-only authoring (list, create, edit chapters/lessons/quiz, roster)
│   ├── components/
│   │   ├── daily-pulse/               # DailyPulseCard, SandboxExercise, QuizQuestion
│   │   └── sandbox/                   # PromptPlayground, ParamControls, TokenCostMeter
│   ├── lib/
│   │   ├── api.ts                     # fetch wrapper against the FastAPI backend
│   │   └── types.ts                   # TS types mirroring backend Pydantic schemas
│   └── package.json
└── docker-compose.yml
```

## Database schema

Five core models (as specced) plus supporting tables the API routes
actually need to hold real data, plus the general-purpose course system:

| Model | Purpose |
|---|---|
| `User` | `email`, `hashed_password`, `role` (RBAC), `track_id` (nullable until onboarding), `common_core_completed_at` (nullable -- NULL is the "still in Common Core" gate) |
| `Track` | The 3 specialization tracks. Common Core is **not** a Track row -- it's `Lesson.track_id IS NULL` |
| `Module` | A named, ordered chapter grouping. Belongs to either a `Track` (`track_id`) or a `Course` (`course_id`), nullable on both, never both at once |
| `Lesson` | `track_id` nullable (NULL = Common Core or a Course lesson -- see "Courses vs. Tracks" below), `module_id` nullable, `title`, `content_markdown`, `order_index`. Course affiliation is derived (`lesson.course_id` property -> `lesson.module.course_id`), not a stored column |
| `DailyPulse` | `pulse_date`, `track_id`, `summary`, `sandbox_exercise`, `quiz_question` + `quiz_choices` (JSON) + `quiz_correct_index`, `status` (draft/published/flagged), `eval_score` |
| `PromptAttempt` | `prompt_text`, `model`, `temperature`, `top_p`, real `input_tokens`/`output_tokens`/`estimated_cost_usd`/`latency_ms`, `served_from_cache` |
| `UserLessonProgress`* | join table: which user completed which lesson, when |
| `SemanticCacheEntry`* | prompt + embedding + cached response, backing the semantic cache |
| `Course`* | `slug`, `title`, `description`, `category` (free text), `instructor_id`, `is_published` -- an arbitrary, instructor-authored course, built from the same `Module`/`Lesson` tables a `Track` uses |
| `Enrollment`* | `user_id` + `course_id`, `enrolled_at`, `due_at` (nullable, no reminder system behind it), `completed_at` (nullable, set automatically) |
| `Quiz`* | One per chapter (`module_id`), `title`, `passing_score` (0-100), `questions` (JSON list of `{question, choices, correct_index}` -- mirrors `DailyPulse.quiz_choices`/`quiz_correct_index`'s shape) |
| `QuizAttempt`* | `user_id`, `quiz_id`, `answers` (JSON list of chosen indices), `score`, `passed`, `attempted_at` -- multiple attempts per user allowed |
| `Certificate`* | `user_id`, `course_id`, `certificate_code` (unique, public lookup key), `issued_at` -- one per (user, course), auto-issued, never duplicated |

\* Not in the original 5-model list, but required for `/users/{id}/progress`,
the semantic cache, and the course system to hold real data rather than
being unimplementable stubs.

## Courses vs. Tracks

The 3 Tracks (Leader/Practitioner/Developer) are this platform's own fixed,
curated curriculum, assigned during onboarding. Courses are the opposite:
arbitrary, instructor-authored, created/edited through the UI, and joined
by choice (enrollment) rather than assignment. They deliberately share the
same `Module` ("chapter") and `Lesson` tables rather than a parallel
chapter/lesson schema -- a `Module` now has both `track_id` and `course_id`
(nullable, mutually exclusive), so lesson rendering, completion tracking,
and the reading UI (`/dashboard/lessons/[id]`) are the exact same code path
either way. Only the top-level container, who can author it, and the
completion mechanics (Common-Core gate vs. enrollment + quiz-passing +
certificate) differ. Completing a lesson (`POST /api/users/lessons/complete`)
checks which container the lesson belongs to and drives the right side
effect -- flipping the Common Core gate for a Track/Common-Core lesson, or
recomputing course progress and auto-issuing a certificate for a Course
lesson -- never both, since a lesson only ever belongs to one.

## Running locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # no API key needed -- runs on your local `claude` CLI login
python scripts/seed.py
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Generate today's pulses manually (normally run by cron):

```bash
cd backend && python scripts/run_daily_pulse.py
```

## Scoping notes -- what's genuinely wired vs. what's a documented extension point

Being direct about this rather than letting it look more finished than it is:

- **SQLite, not Postgres** (per your instruction). Everything goes through
  SQLAlchemy, so swapping `DATABASE_URL` to a Postgres DSN is a one-line
  change if this needs to scale past a single file later.
- **No pgvector/Milvus/Pinecone.** Embeddings (semantic cache, and a future
  RAG-over-lesson-content feature) are stored as JSON float arrays in
  SQLite, compared via brute-force cosine similarity in Python. Fine at
  cache-table scale; the first thing to swap out if the corpus grows large
  enough for that to matter.
- **Runs on a Claude subscription, not a billed API key.** `claude_client.py`
  shells out to the local `claude` CLI (`claude --print`) instead of
  calling a metered API -- flat-rate, nothing to configure beyond having
  `claude` installed and logged in. Two real consequences: (1) there's no
  native structured-output/schema flag the way an API SDK would offer, so
  JSON output is enforced by prompt instruction + parse + one repair
  re-prompt on failure (see `_extract_json`/`generate()`); (2) token counts
  are a ~4-chars/token estimate everywhere, including on stored
  `PromptAttempt` rows, since the CLI doesn't report exact usage on stdout
  -- `token_cost.py`'s dollar figures are therefore illustrative ("what
  this would've cost on metered billing"), not a real charge.
- **Embeddings are local too** (`sentence-transformers`, `all-MiniLM-L6-v2`)
  -- no API key for those either, runs entirely on-device. Same model
  family already used elsewhere in this environment for embeddings, picked
  for consistency.
- **MCP is real but not on the hot path.** `agents/mcp_tools.py` wraps the
  news-fetch and pulse-generation functions as genuine MCP tools (using the
  real `mcp` SDK, runnable standalone over stdio) so an external MCP host
  can call them. The daily cron job itself calls the same underlying
  functions **directly, in-process** -- routing a same-process scheduled
  script through an MCP round-trip would be pure overhead for no benefit.
- **A2A (Agent-to-Agent) is not implemented.** The spec asked for it to help
  orchestrate ingestion/generation, but a single daily job with a clear
  ingest -> generate -> evaluate pipeline (all in `daily_pulse_agent.py`)
  doesn't currently need multiple independently-running agents coordinating
  with each other. The natural extension point, if this grows into e.g. a
  separate "source curation" agent that proposes new RSS feeds and
  negotiates with the pulse-generation agent, would be a second MCP-exposed
  agent communicating over A2A -- not built here since there's nothing
  real for it to coordinate with yet.
- **No Prometheus/Grafana wiring.** `PromptAttempt` and `DailyPulse` already
  capture the numbers you'd want to graph (tokens, cost, latency, eval
  score) -- the next step would be a `/metrics` endpoint
  (`prometheus-fastapi-instrumentator`) exporting them, not built here to
  avoid shipping an observability stack nobody's running yet.
- **RBAC is minimal.** `UserRole` (learner/instructor/admin) exists on the
  model and is checked in exactly one place (`GET /users/{id}/progress`
  refuses to show another user's progress unless you're admin) -- real
  admin/instructor-only routes (editing lessons, reviewing flagged pulses)
  aren't built yet.
- **Token pricing is illustrative**, not pulled from a live pricing API --
  see the comment in `token_cost.py`.
- **Course authoring is append-only, no drag-reorder.** The instructor
  editor (`/dashboard/instructor/courses/[id]/edit`) can add chapters and
  lessons, but there's no PATCH route to reorder or edit an existing
  chapter/lesson after creation -- `order_index` is set to "next available
  slot" on create, so getting the order right means creating things in the
  order you want them to appear. Reordering/editing existing content is the
  natural next route to add, not built here to keep the authoring surface
  small for a first pass.
- **No due-date reminders, no waitlists, no drip-scheduling.**
  `Enrollment.due_at` exists and is shown on the learner dashboard, but
  there's no cron/email job that does anything with it -- same "real column,
  no notification infra behind it" trade-off as `DailyPulse` making the
  same call elsewhere in this README. Course content is also all available
  immediately on enrollment; there's no scheduled/drip release of chapters
  over time.
- **No course review/approval workflow.** `is_published` is a single
  boolean the owning instructor (or an admin) flips directly -- there's no
  draft-review-approve pipeline, and no way for an admin to unpublish
  someone else's course except by using the same owner-or-admin-gated PATCH
  route.
- **Quiz question types are multiple-choice only**, mirroring
  `DailyPulse`'s existing quiz shape (`choices` + `correct_index`) for
  consistency rather than inventing free-text/multi-select grading.
- **No dark theme.** The whole app (including the pre-existing Tracks/Daily
  Pulse/Sandbox/Explore pages, not just the new Courses pages) runs a
  single light, Udemy-style palette -- white background, `#f7f9fa` panels,
  `#d1d7dc` borders, near-black body text, and a purple (`#5624d0`) brand
  color used only for primary actions/links/progress, not decoration. See
  `tailwind.config.ts`'s `brand`/`ink`/`ink-muted`/`surface`/`line` tokens
  and `app/globals.css`. There's no theme toggle or dark-mode media-query
  variant -- if that's wanted later it's a second set of token values
  behind `prefers-color-scheme`, not a rewrite.
