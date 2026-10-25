"""One durable worker; model output never executes tools or submitted code."""
from datetime import datetime,timedelta
from app.models.education import EducationJob,EducationWorker,LessonAmendment,GraderCalibration
from app.models.learning import LearningUnit
from app.models.lesson import Lesson
from app.services.education_queue import claim
from app.services.education_grading import assess,MODELS
from app.services.education_curriculum import build_amendment
from app.services.learning import content_hash


def publish_amendment(db,job,result):
    lesson=db.get(Lesson,job.subject_id)
    unit=db.query(LearningUnit).filter_by(lesson_id=job.subject_id).first()
    base=unit.version if unit else content_hash(lesson) if lesson else None
    if not lesson or base!=job.version or content_hash(lesson)!=job.payload['content_hash']:
        raise ValueError('Base lesson changed during source review')
    existing=db.query(LessonAmendment).filter_by(job_id=job.id).first()
    if existing:return existing
    data=result['amendment']
    evidence=[{**entry,'url':job.payload['url'],'source_sha256':result['source_sha256']} for entry in data['evidence']]
    amendment=LessonAmendment(lesson_id=lesson.id,signal_id=job.payload['signal_id'],job_id=job.id,base_version=base,
                              title=data['title'],markdown=data['markdown'],evidence=evidence,
                              question={key:data[key] for key in ['question','reflection_prompt','reference','rubric']},status='published')
    db.add(amendment);db.flush()
    return amendment


def run_one(factory, *, assessor=None, builder=None, require_calibration=True):
    now=datetime.utcnow()
    with factory() as db:
        heartbeat=db.get(EducationWorker,1)
        if not heartbeat:
            heartbeat=EducationWorker(id=1,heartbeat_at=now);db.add(heartbeat)
        heartbeat.heartbeat_at=now;heartbeat.current_job=None;db.commit()
        calibration=db.get(GraderCalibration,1)
        if require_calibration and (not calibration or not calibration.passed or calibration.model_ids!=list(MODELS) or calibration.checked_at<now-timedelta(days=30)):
            return None
        job=claim(db)
        if not job:return None
        job_id,kind,payload,attempts=job.id,job.kind,job.payload,job.attempts
        heartbeat.current_job=job_id;db.commit()
    try:
        result=(builder or build_amendment)(payload) if kind=='curriculum' else (assessor or assess)(payload)
        with factory() as db:
            job=db.get(EducationJob,job_id)
            if job.status!='running' or job.attempts!=attempts:return job_id
            if kind=='curriculum':
                if result['approved']:
                    amendment=publish_amendment(db,job,result)
                    result['amendment_id']=amendment.id
                    job.status='published'
                else:job.status='needs_review'
                job.passed=False
            else:
                job.status=result['status'];job.passed=result['passed']
            job.result=result;job.finished_at=datetime.utcnow()
            db.flush()
            if kind!='curriculum' and job.passed and payload.get('course_id'):
                from app.services.course_progress import check_and_issue_certificate
                check_and_issue_certificate(db,job.user_id,payload['course_id'])
            db.commit()
    except Exception as error:
        with factory() as db:
            job=db.get(EducationJob,job_id)
            if job and job.status=='running' and job.attempts==attempts:
                job.status='failed';job.passed=False;job.finished_at=datetime.utcnow()
                job.result=dict(message='The assessment could not be verified. Your work is saved; retry or request instructor review.',error_type=type(error).__name__)
                db.commit()
    finally:
        with factory() as db:
            heartbeat=db.get(EducationWorker,1)
            heartbeat.heartbeat_at=datetime.utcnow();heartbeat.current_job=None;db.commit()
    return job_id
