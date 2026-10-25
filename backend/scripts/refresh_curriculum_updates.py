"""Refresh lesson-linked source signals without LLM calls or course rewrites."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.db import SessionLocal
from app.services.curriculum_updates import ingest

if __name__ == '__main__':
    with SessionLocal() as db:
        result = ingest(db)
        from app.services.education_curriculum import enqueue_amendments
        result["amendments_queued"] = enqueue_amendments(db)
        print(json.dumps(result))
        raise SystemExit(1 if len(result['errors']) == 3 else 0)
