"""Inspect only public-source update failures; never reads learner submissions."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.education_curriculum import fetch_evidence

reports=[]
with sqlite3.connect('file:/opt/cortex/backend/ai_academy.db?mode=ro',uri=True) as db:
    jobs=db.execute("select id,status,payload,result from education_jobs where kind='curriculum' order by id desc limit 6").fetchall()
for job_id,status,payload,result in jobs:
    payload,result=json.loads(payload),json.loads(result)
    entry=dict(job_id=job_id,status=status,error_type=result.get('error_type'),source_url=payload['url'],lesson=payload['lesson_title'])
    try:
        source=fetch_evidence(payload['url'])
        entry.update(fetch='ok',characters=len(source),sha256=hashlib.sha256(source.encode()).hexdigest())
    except Exception as error:
        entry.update(fetch='failed',fetch_error_type=type(error).__name__)
        if hasattr(error,'response'):entry['http_status']=error.response.status_code
        if isinstance(error,ValueError):entry['validation']=str(error)[:120]
        else:
            message=str(error).lower()
            entry['transport_signals']=[key for key in ['certificate','ssl','verify','timeout','connection'] if key in message]
    reports.append(entry)
print(json.dumps(reports))
