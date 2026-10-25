"""Durable model jobs, private results and bounded retry policies."""
from datetime import datetime, timedelta
from sqlalchemy import or_
from app.models.education import EducationJob


def enqueue(db, *, key, kind, user_id, subject_id, version, payload):
    existing=db.query(EducationJob).filter_by(request_key=key).first()
    if existing:return existing
    job=EducationJob(request_key=key,kind=kind,user_id=user_id,subject_id=subject_id,version=version,
                     payload=payload,status='queued',result={},passed=False,attempts=0)
    db.add(job);db.flush()
    return job


def public_job(job):
    if not job:return None
    return dict(id=job.id,kind=job.kind,status=job.status,passed=job.passed,version=job.version,
                result=job.result,created_at=job.created_at,finished_at=job.finished_at)


def claim(db):
    now=datetime.utcnow()
    # Recover work abandoned by a crash; never mark it as passed.
    stale=db.query(EducationJob).filter(EducationJob.status=='running',EducationJob.started_at<now-timedelta(minutes=15)).all()
    for job in stale:
        job.status='queued' if job.attempts<3 else 'failed'
        job.result={'message':'Worker interrupted. Retry is available.'}
    db.commit()
    processed=db.query(EducationJob).filter(EducationJob.started_at>=now-timedelta(days=1)).count()
    if processed>=120:return None
    # Student feedback has priority over background amendments.
    job=(db.query(EducationJob).filter_by(status='queued').order_by((EducationJob.kind=='curriculum').asc(),EducationJob.id).first())
    if not job:return None
    changed=(db.query(EducationJob).filter_by(id=job.id,status='queued').update(dict(status='running',started_at=now,attempts=job.attempts+1),synchronize_session=False))
    db.commit()
    return db.get(EducationJob,job.id) if changed else None
