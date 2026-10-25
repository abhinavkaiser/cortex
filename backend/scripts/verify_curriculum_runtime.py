"""Verify real source generation/publication on a private disposable DB copy."""
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory(prefix='cortex-curriculum-check-') as folder:
    database=Path(folder)/'verification.db'
    with sqlite3.connect('file:/opt/cortex/backend/ai_academy.db?mode=ro',uri=True) as source,sqlite3.connect(database) as target:source.backup(target)
    database.chmod(0o600)
    os.environ['DATABASE_URL']='sqlite:///'+str(database)
    from app.core.db import SessionLocal
    from app.models.education import EducationJob,GraderCalibration
    from app.services.education_curriculum import enqueue_amendments,build_amendment,effective_unit
    from app.services.education_worker import publish_amendment
    from app.services.education_grading import MODELS
    from app.models.learning import LearningUnit
    reports=[]
    with SessionLocal() as db:
        calibration=db.get(GraderCalibration,1)
        if not calibration or not calibration.passed or calibration.model_ids!=list(MODELS):raise RuntimeError('Live calibration required')
        previous={row.id for row in db.query(EducationJob).all()}
        queued=enqueue_amendments(db)
        jobs=[row for row in db.query(EducationJob).filter_by(kind='curriculum',status='queued').all() if row.id not in previous]
        for job in jobs:
            report=dict(source=job.payload['url'],lesson=job.payload['lesson_title'])
            try:
                result=build_amendment(job.payload)
                report.update(approved=result['approved'],review=result['review'],evidence_quotes=len(result['amendment']['evidence']))
                if result['approved']:
                    amendment=publish_amendment(db,job,result);db.commit()
                    unit=db.query(LearningUnit).filter_by(lesson_id=job.subject_id).first()
                    if unit:report['served_update_question']=len(effective_unit(db,unit).exercise['questions'])>len(unit.exercise['questions'])
                    reports.append(report);break
            except Exception as error:
                report.update(approved=False,error_type=type(error).__name__)
                if hasattr(error,'errors'):report['validation']=[{key:item[key] for key in ['loc','type','msg']} for item in error.errors(include_input=False)]
            reports.append(report)
    print(json.dumps(dict(passed=any(row.get('approved') for row in reports),queued=queued,results=reports,production_writes=False)))
