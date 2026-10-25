# Advanced learning release

This release replaces self-review-only completion with durable rubric assessment,
adds six specialization projects (18 milestones), six advanced ML/research lessons,
actual prompt comparisons, saved drafts, appeals, and baseline/transfer/delayed checks.
Source refreshes can now publish source-backed teaching additions and new practice
questions. Every positive grading criterion requires an exact quote from submitted
work; objective benchmark failures cannot be overridden into passes.

## Release gate

The existing production runner deploys through **Learning curriculum release**.
First run the workflow on `codex/complete-learning` with `deploy=false`. Calibration
must correctly distinguish supported work, empty work, prompt injection and incorrect
calculations using both constrained models. It records resolved model versions.
A failed calibration leaves grading paused and prevents the production switch.

On 2026-10-25 the production Claude access token was expired (401), and its existing
refresh token was rejected (`invalid_grant`). Account sign-in is required as
`cortexapp`; GitHub access and the deployment runner already work. No password or
private token belongs in this repository. Once signed in, rerun preflight/calibration.
Do not substitute test fixtures for this gate.

After review/merge, dispatch the workflow on `main` with `deploy=true`. Deployment:

1. Requires the expected host, root runner, clean checkout, correct app owner and 2 GB free.
2. Makes a consistent private SQLite backup, tests publication against a copy and runs backend tests.
3. Builds separately as `cortexapp`, calibrates real models, then publishes both teaching packs.
4. Restarts only Cortex's two PM2 applications, verifies public health/page responses,
   installs the durable worker and daily calibration/source-refresh timers.
5. On failure restores affected content/build/code and service definitions while preserving
   attempts and progress. Newly added courses are hidden, never destructively deleted.

The deployment script intentionally refuses dependency changes; those require a
separate procedure. Never run seed scripts or replace the live database with an export.

## Operations

- `cortex-learning-worker.service`: one durable worker, private process lock, crash recovery.
- `cortex-grader-calibration.timer`: daily 05:30 UTC; failures pause automated work.
- `cortex-curriculum-refresh.timer`: daily 06:15 UTC; up to three amendment jobs per day.
- `/api/studio/status`: authenticated worker/calibration and publication status.
- `/dashboard/instructor/review`: disagreements, appeals and unpublished source failures.
- `/dashboard/outcomes`: personal evidence, optional pilot consent and admin aggregates.

Queued work survives restarts. Provider/format errors award no pass. Both reviewers
must support a pass; large disagreement requests instructor review. Instructors
cannot approve their own work. Synthetic benchmarks support narrow case checks;
submitted arbitrary code is inspected, never executed by the server. Real prompt
experiments run through the constrained model adapter.

## Verification and limits

Local verification: 47 backend tests, TypeScript and optimized Next.js build passed.
Disposable-database publication, idempotence, rollback and retained learner-record
checks passed. Browser validation passed registration, all 21 path units, the
pending-grade completion gate, six project listings, a baseline check, draft
autosave/reload, a recorded development experiment, outcomes and mobile layout.
It did not simulate or validate model grading. Workspace reports retain the script
and screenshots. [Server validation run](https://github.com/abhinavkaiser/cortex/actions/runs/40173684090)
confirmed the production revision remains `5dda923` and all calibration calls fail
with expired-login 401 responses. Live calibration and deployment remain blocked
until account sign-in succeeds.

Two models from one provider are fallible correlated reviewers, not independent
accreditation. Source quote verification and a second review reduce unsupported
amendments but do not guarantee factual accuracy. The instructor can withdraw an
amendment; base lesson edits invalidate stale amendments and practice credit.
The six-item parallel checks are preliminary instruments, not standardized ability
scores. Genuine student engagement and durable learning require real follow-up;
see [pilot protocol](../docs/learning-pilot.md). No synthetic learner results are
inserted into production evidence or claimed as educational impact.
