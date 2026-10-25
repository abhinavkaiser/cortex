# Embeddings and LLM fine-tuning course

A dedicated course adds 14 authored, versioned lessons in seven chapters to
`/dashboard/courses/embeddings-and-llm-fine-tuning`. The guided path grows from
21 to 35 units. Prerequisites are the technical bridge; completing the research
path is not required to open this course.

The chapters cover:

1. Embedding representations, cosine similarity, ingestion, chunking and provenance.
2. Exact/ANN/hybrid search, retrieval evaluation and embedding-model adaptation.
3. Adaptation strategy, instruction-data quality, rights and leakage-resistant splits.
4. Chat templates, loss masking, packing, SFT optimization and reproducibility.
5. LoRA parameter arithmetic, adapter dependencies, QLoRA and complete memory budgets.
6. Paired evaluation, regressions, DPO and preference-label quality.
7. Distillation, release manifests, monitoring and compatible rollback.

Each lesson includes a worked case, two decisions with four choices and
answer-specific feedback, a reference response, four reasoning criteria, and
primary technical references. Written work uses the existing durable grading,
revision and appeal flow. The course teaches concepts, calculations and experiment
plans; it does not claim a GPU lab or an executed embedding/LLM training run.

`backend/scripts/publish_embeddings_path.py` is dry-run by default. Publication is
additive/idempotent, snapshots earlier teaching, preserves attempts and refuses
unrecognized instructor edits or cross-course slug collisions. The existing
backed-up production release now validates and applies this publisher alongside
the foundation and research packs. Rollback hides a newly added course and retains
learner work. New topic mappings connect all 14 lessons to reviewed source updates.

Validation: 53 backend tests, optimized Next.js build, and disposable-database
publication/dry-run/idempotence/rollback/redeployment checks passed. Source content
uses worked arithmetic and supplied hypothetical cases rather than invented model
benchmark or student outcomes. Numerical and labeling claims were checked against
the referenced concepts; no new training dependencies or paid service are added.
