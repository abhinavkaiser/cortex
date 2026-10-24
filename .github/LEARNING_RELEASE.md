# Guided learning release

This release completes a foundation-to-technical-bridge learning sequence. It
rewrites nine foundation lessons, adds six bridge units and corrects specific
claims in three developer lessons. Each reviewed unit has an objective,
prerequisites, five explanatory sections, source references, a review deadline,
two scenario decisions with choice-specific feedback, and a written reflection
with a reference answer and rubric. Four aligned chapter assessments and review
decks replace foundation material or add bridge material.

Written explanations and the downloadable project are self-reviewed. Decision
practice allows retries. Neither is presented as independently verified mastery.
The rest of the existing catalog is available with an explicit unreviewed notice;
its advanced projects, assessments and content still need deeper reconstruction.

## Publication and data

`backend/scripts/publish_learning_path.py` is dry-run by default; `--apply`
commits one transaction. Only additive tables are introduced. It snapshots the
original lesson content and assessment material, preserves lesson IDs, learner
records, certificates and attempts, and refuses unknown instructor edits.
Publication is idempotent. Revised quizzes tag new attempts with the current
question-set version, so a historical pass cannot clear a replacement quiz.

Practice APIs enforce authentication, ownership of responses, choice ranges,
reflection length, current content hashes and revision versions. Correct current
practice is required for new completion/certificate decisions in reviewed units.
Reflection length checks do not grade the quality of reasoning.

## Freshness

Fixed Hugging Face, OpenAI and Google Research RSS feeds supply dated source
signals. Undated, future, older-than-30-day and duplicate items are excluded.
Keyword matching links items to relevant lessons. Headlines are not endorsed
facts or verified amendments. Feed failures and last-check status are visible.
The refresh does not call an LLM or rewrite lessons automatically.

The deployment installs `cortex-curriculum-refresh.timer`, daily at 06:15 UTC
with up to five minutes jitter and catch-up after downtime. The service runs as
`cortexapp` and is independent of the existing Daily Pulse job. Daily Pulse now
shows the latest published item per specialization, keeps its actual date and
explicitly labels earlier-day content. Flagged items stay hidden.

## Release procedure

The trusted `Learning curriculum release` workflow has no PR trigger. Its deploy
input only executes from `main` on the repository's existing production runner.

The script checks server identity, the clean checkout, available space, runtime
and application owner. It creates a consistent, integrity-checked SQLite backup
under a root-only `/opt/cortex-backups/learning-*` directory. It validates the
publication on a disposable production copy and runs isolated API tests before
changing the live application. It builds locked frontend dependencies in a
separate temporary directory as `cortexapp`; live node_modules are preserved.

Only `cortex-backend` and `cortex-frontend` are stopped/restarted. Environment
files, uploaded media, learner data, nginx and other PM2 applications are
preserved. The backend is briefly unavailable during publication and restart.
The previous frontend build is retained, and old hashed assets are carried into
the new build for existing browser sessions.

After switching, both production health and the new frontend route must pass.
On failure, the script restores the previous code/build and original affected
teaching content, retains learner attempts and hides a newly added bridge course.
It does not replace the live database wholesale or discard concurrent learner
records. Retained root-only backups permit manual recovery if needed. Subsequent
releases with a different schema or dependency change need a fresh procedure.

## Validation

- `backend/.venv/bin/python -m pytest backend/tests -q`
- `backend/.venv/bin/python -m unittest discover -s backend/content/labs -v`
- `npm run build` from `frontend/`
- Publication dry-run, apply and reapply on a disposable copy of the course export.
- Browser journey: registration, path selection, wrong-answer feedback, explanation,
  revision, completion, persisted work, mobile layout and project ZIP download.

Generated-question baselines check that choosing the longest answer does not
exceed 50% on either the 30 guided decisions or the 15 revised assessment items.
This catches one known flaw; it is not an independent validation of assessment
quality or learner outcomes.

The playground's unsupported sampling/output-limit sliders are disabled and
labeled as illustrative, rather than implying that changing them affects the
CLI-backed generation. Model selection remains available.
