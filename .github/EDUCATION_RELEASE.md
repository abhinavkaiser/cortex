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
calculations using both constrained models. It records requested model identifiers; Codex exec does not guarantee a resolved release identifier.
A failed calibration leaves grading paused and prevents the production switch.

The runtime now uses **Codex CLI with a ChatGPT subscription**, replacing the
expired Claude account. API access is not required. Prepare the pinned app-only CLI
using the release workflow `prepare_codex=true`, then complete subscription sign-in:

```bash
sudo -iu cortexapp /opt/cortex-codex/node_modules/.bin/codex login --device-auth
```

GitHub access and the deployment runner already work. The server account needs its
own sign-in; maintenance-environment credentials are never copied. No password or
private token belongs in this repository. Once signed in, rerun preflight/calibration.
Release runs are manual; pushing development changes no longer triggers calibration.
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

Local verification: 51 backend tests, TypeScript and optimized Next.js build passed.
Disposable-database publication, idempotence, rollback and retained learner-record
checks passed. Browser validation passed registration, all 21 path units, the
pending-grade completion gate, six project listings, a baseline check, draft
autosave/reload, a recorded development experiment, outcomes and mobile layout.
It did not simulate or validate model grading. Workspace reports retain the script
and screenshots. On 2026-10-25 the app-owned ChatGPT subscription was verified on
Hetzner. Both configured models (`gpt-6-luna`, `gpt-6.1-sol`) passed fixed-prompt
connection checks with safety-critical tool toggles verified against the installed
CLI. [Live grading calibration](https://github.com/abhinavkaiser/cortex/actions/runs/40183943238)
passed all four controls: supported work 83%, empty work 0%, injection 0%, incorrect
calculations 0%. Each control was reviewed by both models. Production deployment
runs these controls again before switching the application.


Two models from the same provider are fallible correlated reviewers, not independent
accreditation. Source quote verification and a second review reduce unsupported
amendments but do not guarantee factual accuracy. The instructor can withdraw an
amendment; base lesson edits invalidate stale amendments and practice credit.
The six-item parallel checks are preliminary instruments, not standardized ability
scores. Genuine student engagement and durable learning require real follow-up;
see [pilot protocol](../docs/learning-pilot.md). No synthetic learner results are
inserted into production evidence or claimed as educational impact.

## Source availability and runtime publication

The first subscription release deployed successfully in
[run 40184089435](https://github.com/abhinavkaiser/cortex/actions/runs/40184089435).
Read-only production API and browser checks confirmed 21 units, six projects,
working subscription completion, calibrated grading and an active worker.

Its first update attempts encountered HTTP 403 from one publisher. Scheduling now
checks evidence before model work, skips inaccessible sources, uses distinct articles
and lessons, preserves the correct audience and prioritizes explicit topic matches.
Snapshots retain source text, retrieval time and SHA-256 for exact quote validation.
Network work finishes before queue writes. Generation and review use native Codex
JSON schemas plus the existing local factual, quote, question and version checks.
Failed transport requests do not consume the three daily model-generation slots.

[Real source verification](https://github.com/abhinavkaiser/cortex/actions/runs/40185001086)
passed on a private disposable database copy: one relevant teaching addition,
five verified source quotes, separate factual/educational approval and an added
served practice question. No production learner records were written by this check.

The **Refresh public daily learning content** workflow can run the existing Daily
Pulse job on demand, without changing the normal daily schedule. Publication still
requires the factual and answer-key checks; a failed item stays unpublished.
