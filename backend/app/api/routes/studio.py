"""Projects, durable feedback, reviewed updates and measured learning evidence."""
from datetime import datetime,timedelta
from typing import Literal
import json

from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,StrictInt
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.api.routes.learning import visible_lesson
from app.core.db import get_db
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.learning import LearningUnit,PracticeAttempt
from app.models.user import User
from app.models.education import (AssessmentAppeal,AmendmentAttempt,EducationJob,EducationWorker,EvidenceAttempt,
    GraderCalibration,LearningEvent,LearningStudyAssignment,LessonAmendment,ProjectSubmission,ProjectExperiment,ProjectDraft)
from app.services.education_curriculum import amendments,effective_unit
from app.services.education_grading import MODELS,practice_payload
from app.services.education_queue import enqueue,public_job
from app.services.education_outcomes import (check_questions,cohort_report,course_project_passed,evidence_state,milestones_passed,
    outcomes,presentation,study_status,PROTOCOL)
from app.services.project_benchmarks import benchmark
from app.services.learning import unit_status
from content.advanced.projects import PROJECTS,project_by_slug,project_version
from content.advanced.evidence_checks import SKILLS

router=APIRouter(prefix='/api/studio',tags=['learning studio'])


class StrictBody(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ProjectWork(StrictBody):
    version:str=Field(min_length=1,max_length=64)
    milestone:StrictInt=Field(ge=0,le=2)
    artifact:dict
    report:str=Field(min_length=200,max_length=30000)


class CheckWork(StrictBody):
    phase:Literal['baseline','transfer','retention','reassessment']
    answers:list[StrictInt]=Field(min_length=6,max_length=6)


class AppealWork(StrictBody):
    reason:str=Field(min_length=40,max_length=4000)


class ReviewWork(StrictBody):
    passed:bool
    score:StrictInt=Field(ge=0,le=100)
    explanation:str=Field(min_length=60,max_length=6000)


class StudyWork(StrictBody):
    consent:bool


class ActivityWork(StrictBody):
    lesson_id:StrictInt
    seconds:StrictInt=Field(ge=0,le=60)


def project_visible(db,slug,user):
    spec=project_by_slug(slug)
    if not spec:raise HTTPException(404,'Project not found')
    course=db.query(Course).filter_by(slug=spec['course']).first()
    if not course or (not course.is_published and course.instructor_id!=user.id and user.role.value!='admin'):
        raise HTTPException(404,'Project not found')
    return spec,course


def can_review(db,user,job):
    if user.role.value=='admin':return True
    course=db.get(Course,job.payload.get('course_id')) if job.payload.get('course_id') else None
    return bool(course and user.role.value=='instructor' and course.instructor_id==user.id)


def own_job(db,job_id,user,reviewer=False):
    job=db.get(EducationJob,job_id)
    if not job or (job.user_id!=user.id and not (reviewer and can_review(db,user,job))):
        raise HTTPException(404,'Feedback not found')
    return job


def project_progress(db,user,spec):
    rows=db.query(ProjectSubmission).filter_by(user_id=user.id,project_slug=spec['slug'],version=project_version(spec)).order_by(ProjectSubmission.id.desc()).all()
    milestones=[]
    for index,definition in enumerate(spec['milestones']):
        submissions=[];passed=False
        for work in rows:
            if work.milestone!=index:continue
            job=db.query(EducationJob).filter_by(kind='project',subject_id=work.id,user_id=user.id).first()
            passed=passed or bool(job and job.status=='graded' and job.passed)
            submissions.append(dict(id=work.id,report=work.report,artifact=work.artifact,benchmark=work.benchmark,submitted_at=work.submitted_at,assessment=public_job(job)))
        experiments=db.query(ProjectExperiment).filter_by(user_id=user.id,project_slug=spec['slug'],milestone=index,version=project_version(spec)).order_by(ProjectExperiment.id.desc()).limit(8).all()
        draft=db.query(ProjectDraft).filter_by(user_id=user.id,project_slug=spec['slug'],milestone=index,version=project_version(spec)).first()
        milestones.append(dict(**definition,index=index,passed=passed,submissions=submissions[:10],draft=dict(artifact=draft.artifact_text,report=draft.report,updated_at=draft.updated_at) if draft else None,
                               experiments=[dict(id=e.id,artifact=e.artifact,benchmark=e.metrics,created_at=e.created_at,assessment=public_job(db.query(EducationJob).filter_by(kind='prompt_experiment',subject_id=e.id,user_id=user.id).first())) for e in experiments]))
    return milestones


@router.get('/projects')
def projects(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    result=[]
    for spec in PROJECTS:
        try:_,course=project_visible(db,spec['slug'],user)
        except HTTPException:continue
        milestones=project_progress(db,user,spec)
        result.append({key:spec[key] for key in ['slug','title','audience','hours','skill','brief','course']} |
                      dict(version=project_version(spec),milestones_passed=sum(m['passed'] for m in milestones),milestones_total=len(milestones),
                           completed=course_project_passed(db,user.id,spec['course'])))
    return result


@router.get('/projects/{slug}')
def project_detail(slug:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    spec,course=project_visible(db,slug,user)
    readings={lesson.slug:lesson for lesson in db.query(Lesson).all() if lesson.module and lesson.module.course.is_published}
    milestones=project_progress(db,user,spec)
    for milestone in milestones:
        milestone['reading']=[dict(id=readings[key].id,title=readings[key].title) for key in milestone['reading'] if key in readings]
    return {key:spec[key] for key in ['slug','title','audience','hours','skill','brief','evidence','course']} | dict(version=project_version(spec),milestones=milestones,milestones_passed=sum(item['passed'] for item in milestones),milestones_total=len(milestones),completed=course_project_passed(db,user.id,spec['course']),evidence_check=evidence_state(db,user.id,spec['skill']))


@router.post('/projects/{slug}/submissions',status_code=202)
def submit_project(slug:str,body:ProjectWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    spec,course=project_visible(db,slug,user)
    if body.version!=project_version(spec):raise HTTPException(409,'Project changed. Reload the brief before submitting.')
    if len(body.report.strip())<200:raise HTTPException(422,'Provide a substantive report of at least 200 characters')
    if not db.query(EvidenceAttempt).filter_by(user_id=user.id,skill=spec['skill'],phase='baseline').first():
        raise HTTPException(409,'Complete the baseline check before submitting the first milestone')
    progress=project_progress(db,user,spec)
    if any(not entry['passed'] for entry in progress[:body.milestone]):raise HTTPException(409,'Pass the preceding milestone before submitting this one')
    pending=db.query(EducationJob).filter(EducationJob.user_id==user.id,EducationJob.status.in_(['queued','running'])).count()
    if pending>=5:raise HTTPException(429,'Five assessments are pending. Wait for feedback before submitting more work.')
    try:computed=benchmark(spec,body.milestone,body.artifact)
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error))
    work=ProjectSubmission(user_id=user.id,project_slug=slug,milestone=body.milestone,version=body.version,
                           artifact=body.artifact,report=body.report.strip(),benchmark=computed)
    db.add(work);db.flush()
    definition=spec['milestones'][body.milestone]
    experiments=db.query(ProjectExperiment).filter_by(user_id=user.id,project_slug=slug,milestone=body.milestone,version=body.version).order_by(ProjectExperiment.id.desc()).limit(8).all()
    if slug=='team-prompt-evaluation' and body.milestone==1:
        measured=next((e for e in experiments if e.metrics.get('status')=='completed' and e.metrics.get('results')),None)
        measured=(db.query(ProjectExperiment).filter_by(user_id=user.id,project_slug=slug,milestone=1,version=body.version)
                  .filter(ProjectExperiment.metrics['status'].as_string()=='completed').order_by(ProjectExperiment.id.desc()).first())
        computed={**computed,'checks':{**computed['checks'],'measured_prompt_run':measured is not None,
                 'reported_outcomes_match':bool(measured and body.artifact.get('baseline')==measured.metrics['results']['baseline']['correct'] and body.artifact.get('candidate')==measured.metrics['results']['candidate']['correct'])}}
        work.benchmark=computed
        if measured and all(e.id!=measured.id for e in experiments):experiments.append(measured)
    payload=dict(title=spec['title']+' — '+definition['title'],case=spec['evidence'],task=definition['task'],
                 report=work.report,rubric=definition['rubric'],artifact=work.artifact,benchmark=computed,course_id=course.id,
                 recorded_experiments=[dict(id=e.id,configuration=e.artifact,result=e.metrics,recorded_at=e.created_at.isoformat()) for e in experiments])
    job=enqueue(db,key=f'project:{work.id}',kind='project',user_id=user.id,subject_id=work.id,version=work.version,payload=payload)
    db.commit()
    return dict(submission_id=work.id,benchmark=computed,assessment=public_job(job))


@router.get('/jobs/{job_id}')
def feedback(job_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return public_job(own_job(db,job_id,user,reviewer=True))


@router.post('/jobs/{job_id}/retry',status_code=202)
def retry(job_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    job=own_job(db,job_id,user,reviewer=True)
    if job.user_id!=user.id and not (job.kind=='curriculum' and can_review(db,user,job)):raise HTTPException(403,'Cannot retry another learner’s assessment')
    if job.status!='failed' or job.attempts>=3:raise HTTPException(409,'Only failed assessments with fewer than three processing attempts can be retried')
    job.status='queued';job.passed=False;job.result={};db.commit()
    return public_job(job)


@router.post('/practices/{attempt_id}/feedback',status_code=202)
def request_feedback(attempt_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    attempt=db.get(PracticeAttempt,attempt_id)
    if not attempt or attempt.user_id!=user.id:raise HTTPException(404,'Attempt not found')
    lesson=visible_lesson(db,attempt.lesson_id,user)
    unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
    if not unit:raise HTTPException(404,'Practice not found')
    unit=effective_unit(db,unit)
    if unit.version!=attempt.version or unit_status(unit,lesson)=='changed_since_review':raise HTTPException(409,'Submit a current practice attempt before requesting feedback')
    job=enqueue(db,key=f'practice:{attempt.id}',kind='practice',user_id=user.id,subject_id=attempt.id,version=unit.version,payload=practice_payload(attempt,lesson,unit.exercise))
    db.commit();return public_job(job)


@router.post('/jobs/{job_id}/appeal')
def appeal(job_id:int,body:AppealWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    job=own_job(db,job_id,user)
    if job.kind not in ('practice','project') or job.status in ('queued','running'):raise HTTPException(409,'Wait for the assessment before requesting instructor review')
    record=db.query(AssessmentAppeal).filter_by(job_id=job.id).first()
    if record:return dict(id=record.id,status=record.status)
    record=AssessmentAppeal(job_id=job.id,reason=body.reason.strip());db.add(record);db.commit()
    return dict(id=record.id,status=record.status)


@router.get('/review')
def review_queue(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role.value not in ('admin','instructor'):raise HTTPException(403,'Instructor access required')
    rows=db.query(EducationJob).filter(EducationJob.status.in_(['needs_review','failed','graded'])).order_by(EducationJob.id.desc()).limit(300).all()
    result=[]
    for job in rows:
        if not can_review(db,user,job):continue
        request=db.query(AssessmentAppeal).filter_by(job_id=job.id,status='open').first()
        if job.status!='needs_review' and not request and not (job.kind=='curriculum' and job.status=='failed'):continue
        work=job.payload
        if job.kind=='curriculum':work=dict(title=job.payload['lesson_title']+' — source update',case=job.payload['source_title']+'\n'+job.payload['url'],task='Inspect source evidence and the independent review before retrying a failed update or preparing a corrected draft.',report=job.result.get('amendment',{}).get('markdown',job.result.get('message','')),rubric=[])
        result.append(dict(assessment=public_job(job),work=work,appeal=dict(id=request.id,reason=request.reason) if request else None))
    return result[:50]


@router.post('/jobs/{job_id}/review')
def review(job_id:int,body:ReviewWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    job=own_job(db,job_id,user,reviewer=True)
    if not can_review(db,user,job):raise HTTPException(403,'Only the owning instructor or an admin can grade this work')
    if job.kind not in ('practice','project') or job.status in ('queued','running'):raise HTTPException(409,'This job is not ready for instructor grading')
    if job.user_id==user.id and body.passed:raise HTTPException(403,'Self-approval is not an independent assessment; revise the work or ask another instructor')
    if body.passed and (body.score<75 or not all(v is True for v in job.payload.get('benchmark',{}).get('checks',{}).values())):
        raise HTTPException(422,'A pass requires at least 75 and all objective checks; failed artifacts must be revised')
    original=job.result
    job.result=dict(score=body.score,passed=body.passed,reviewer='instructor',explanation=body.explanation,original_assessment=original)
    job.status='graded';job.passed=body.passed;job.finished_at=datetime.utcnow()
    request=db.query(AssessmentAppeal).filter_by(job_id=job.id).first()
    if not request:request=AssessmentAppeal(job_id=job.id,reason='Instructor review of assessment');db.add(request)
    request.status='resolved';request.reviewer_id=user.id;request.resolution=body.explanation
    db.flush()
    from app.services.course_progress import check_and_issue_certificate
    check_and_issue_certificate(db,job.user_id,job.payload['course_id'])
    db.commit();return public_job(job)


@router.get('/checks/{skill}/{phase}')
def get_check(skill:str,phase:Literal['baseline','transfer','retention','reassessment'],user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if skill not in SKILLS:raise HTTPException(404,'Skill not found')
    record_phase=phase
    if phase=='reassessment':
        prior=(db.query(EvidenceAttempt).filter(EvidenceAttempt.user_id==user.id,EvidenceAttempt.skill==skill,EvidenceAttempt.phase.like('reassessment_%')).order_by(EvidenceAttempt.id.desc()).all())
        transfer=db.query(EvidenceAttempt).filter_by(user_id=user.id,skill=skill,phase='transfer').first()
        if not transfer:raise HTTPException(409,'Complete the original transfer check before reassessment')
        latest=prior[0] if prior else transfer
        project=next(p for p in PROJECTS if p['skill']==skill)
        revised=(db.query(ProjectSubmission).join(EducationJob,(EducationJob.subject_id==ProjectSubmission.id)&(EducationJob.kind=='project'))
                 .filter(ProjectSubmission.user_id==user.id,ProjectSubmission.project_slug==project['slug'],ProjectSubmission.milestone==2,
                         ProjectSubmission.version==project_version(project),EducationJob.passed.is_(True),EducationJob.status=='graded',
                         EducationJob.finished_at>latest.created_at).first())
        if not revised:raise HTTPException(409,'Revise the final milestone after your last check and receive a passing assessment before reassessment')
        record_phase='reassessment_'+str(len(prior)+1)
    existing=db.query(EvidenceAttempt).filter_by(user_id=user.id,skill=skill,phase=record_phase).first()
    if existing:return dict(completed=True,score=existing.score,questions=[dict(question=q['question'],choices=q['choices']) for q in existing.snapshot['questions']],feedback=[dict(correct=a==q['correct_index'],explanation=q['explanation']) for a,q in zip(existing.answers,existing.snapshot['questions'])])
    state=evidence_state(db,user.id,skill)
    if phase!='baseline' and state['baseline'] is None:raise HTTPException(409,'Take the baseline check first')
    if phase=='transfer':
        project=next(p for p in PROJECTS if p['skill']==skill)
        if not milestones_passed(db,user.id,project):raise HTTPException(409,'Pass all project milestones before the transfer check')
    if phase=='retention' and not state['retention_available']:raise HTTPException(409,'The delayed check opens seven days after the transfer check')
    return dict(completed=False,questions=[dict(question=q['question'],choices=q['choices']) for q in check_questions(user.id,skill,record_phase)],phase=phase,record_phase=record_phase,skill=skill)


@router.post('/checks/{skill}')
def submit_check(skill:str,body:CheckWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    state=get_check(skill,body.phase,user,db)
    if state['completed']:raise HTTPException(409,'This check is already recorded; use a later phase to measure progress')
    record_phase=state.get('record_phase',body.phase)
    bank=check_questions(user.id,skill,record_phase)
    if any(a<0 or a>=len(q['choices']) for a,q in zip(body.answers,bank)):raise HTTPException(422,'Choose a valid answer for each item')
    score=round(100*sum(a==q['correct_index'] for a,q in zip(body.answers,bank))/len(bank))
    record=EvidenceAttempt(user_id=user.id,skill=skill,phase=record_phase,variant=3+int(record_phase.split('_')[1]) if record_phase.startswith('reassessment_') else {'baseline':0,'transfer':1,'retention':2}[body.phase],
                           answers=body.answers,score=score,snapshot=dict(protocol=PROTOCOL,instrument='parallel-six-item-v1',questions=bank,presentation=presentation(user.id),
                               curriculum_versions={str(unit.lesson_id):effective_unit(db,unit).version for unit in db.query(LearningUnit).all()},
                               project_versions={project['slug']:project_version(project) for project in PROJECTS}))
    db.add(record);db.flush()
    if body.phase in ('transfer','reassessment','retention'):
        from app.services.course_progress import check_and_issue_certificate
        project=next(p for p in PROJECTS if p['skill']==skill)
        course=db.query(Course).filter_by(slug=project['course']).first()
        if course:check_and_issue_certificate(db,user.id,course.id)
    db.commit()
    return dict(score=score,feedback=[dict(correct=a==q['correct_index'],explanation=q['explanation']) for a,q in zip(body.answers,bank)],state=evidence_state(db,user.id,skill))


@router.get('/outcomes')
def get_outcomes(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return outcomes(db,user.id)


@router.get('/study')
def get_study(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return study_status(db,user.id)


@router.post('/study')
def set_study(body:StudyWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.email=='demo@cortex.ai':raise HTTPException(409,'Use a personal account for the optional learning pilot')
    record=db.query(LearningStudyAssignment).filter_by(user_id=user.id).first()
    if not record:record=LearningStudyAssignment(user_id=user.id,arm=presentation(user.id),protocol=PROTOCOL);db.add(record)
    if body.consent and not record.consent:record.consented_at=datetime.utcnow()
    record.consent=body.consent;db.commit();return study_status(db,user.id)


@router.get('/study/report')
def study_report(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role.value!='admin':raise HTTPException(403,'Admin access required')
    return cohort_report(db)


@router.post('/activity')
def activity(body:ActivityWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    visible_lesson(db,body.lesson_id,user)
    now=datetime.utcnow();day=now.date().isoformat()
    row=db.query(LearningEvent).filter_by(user_id=user.id,lesson_id=body.lesson_id,day=day).first()
    if not row:
        row=LearningEvent(user_id=user.id,lesson_id=body.lesson_id,day=day,active_seconds=0,last_seen_at=now);db.add(row)
    else:
        elapsed=max(0,int((now-row.last_seen_at).total_seconds()))
        row.active_seconds+=max(0,min(body.seconds,elapsed,60,7200-row.active_seconds))
        row.last_seen_at=now
    db.commit();return dict(recorded=True)


@router.get('/lessons/{lesson_id}/amendments')
def lesson_amendments(lesson_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    lesson=visible_lesson(db,lesson_id,user)
    unit=db.query(LearningUnit).filter_by(lesson_id=lesson_id).first()
    from app.services.learning import content_hash
    base=unit.version if unit else content_hash(lesson)
    result=[]
    for item in amendments(db,lesson_id):
        if item.base_version!=base:continue
        attempted=db.query(AmendmentAttempt).filter_by(user_id=user.id,amendment_id=item.id).order_by(AmendmentAttempt.id.desc()).first()
        result.append(dict(id=item.id,title=item.title,markdown=item.markdown,evidence=item.evidence,published_at=item.published_at,
                           question={k:item.question['question'][k] for k in ['question','choices']},
                           last_answer=dict(selected=attempted.selected,correct=attempted.correct,feedback=item.question['question']['feedback'][attempted.selected]) if attempted else None))
    return result


class AmendmentAnswer(StrictBody):
    selected:StrictInt=Field(ge=0,le=3)


@router.post('/amendments/{amendment_id}/answer')
def answer_amendment(amendment_id:int,body:AmendmentAnswer,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    item=db.get(LessonAmendment,amendment_id)
    if not item or item.status!='published':raise HTTPException(404,'Update not found')
    lesson=visible_lesson(db,item.lesson_id,user)
    unit=db.query(LearningUnit).filter_by(lesson_id=lesson.id).first()
    from app.services.learning import content_hash
    if item.base_version != (unit.version if unit else content_hash(lesson)):
        raise HTTPException(409,'This update belongs to an older lesson version')
    question=item.question['question'];correct=body.selected==question['correct_index']
    db.add(AmendmentAttempt(user_id=user.id,amendment_id=item.id,selected=body.selected,correct=correct));db.commit()
    return dict(correct=correct,feedback=question['feedback'][body.selected])


@router.post('/amendments/{amendment_id}/withdraw')
def withdraw_amendment(amendment_id:int,body:AppealWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    item=db.get(LessonAmendment,amendment_id)
    if not item:raise HTTPException(404,'Update not found')
    job=db.get(EducationJob,item.job_id)
    if not can_review(db,user,job):raise HTTPException(403,'Owning instructor or admin required')
    item.status='withdrawn';job.result={**job.result,'withdrawal':dict(reason=body.reason,reviewer_id=user.id)};db.commit()
    return dict(withdrawn=True)


@router.get('/status')
def status(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    worker=db.get(EducationWorker,1);calibration=db.get(GraderCalibration,1)
    active=db.get(EducationJob,worker.current_job) if worker and worker.current_job else None
    working=bool(active and active.status=='running' and active.started_at and active.started_at>datetime.utcnow()-timedelta(minutes=15))
    return dict(worker_online=bool(worker and (working or worker.heartbeat_at>datetime.utcnow()-timedelta(minutes=5))),
                worker_last_seen=worker.heartbeat_at if worker else None,
                grading_calibrated=bool(calibration and calibration.passed and calibration.model_ids==list(MODELS) and calibration.checked_at>datetime.utcnow()-timedelta(days=30)),
                calibration_date=calibration.checked_at if calibration else None,
                queued=db.query(EducationJob).filter_by(user_id=user.id,status='queued').count(),
                published_updates=db.query(LessonAmendment).filter_by(status='published').count(),
                curriculum_jobs={state:db.query(EducationJob).filter_by(kind='curriculum',status=state).count() for state in ['queued','running','published','needs_review','failed']},
                model_ids=list(MODELS))


@router.get('/history')
def history(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    jobs=(db.query(EducationJob).filter(EducationJob.user_id==user.id,EducationJob.kind.in_(['practice','project']))
          .order_by(EducationJob.id.desc()).limit(30).all())
    return [dict(title=job.payload['title'],assessment=public_job(job)) for job in jobs]


class ExperimentWork(StrictBody):
    version:str=Field(min_length=1,max_length=64)
    milestone:StrictInt=Field(ge=0,le=2)
    artifact:dict


@router.post('/projects/{slug}/experiment')
def experiment(slug:str,body:ExperimentWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    spec,course=project_visible(db,slug,user)
    if body.version!=project_version(spec):raise HTTPException(409,'Reload the current project before running an experiment')
    today=datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
    if db.query(ProjectExperiment).filter(ProjectExperiment.user_id==user.id,ProjectExperiment.created_at>=today).count()>=100:
        raise HTTPException(429,'Daily experiment limit reached; your previous results are saved')
    try:result=benchmark(spec,body.milestone,body.artifact,preview=True)
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error))
    record=ProjectExperiment(user_id=user.id,project_slug=slug,milestone=body.milestone,version=body.version,artifact=body.artifact,metrics=result)
    db.add(record);db.commit()
    return dict(id=record.id,benchmark=result,note='Recorded development experiment. Change one factor and compare before writing your report.')


class DraftWork(StrictBody):
    version:str=Field(min_length=1,max_length=64)
    milestone:StrictInt=Field(ge=0,le=2)
    artifact_text:str=Field(max_length=10000)
    report:str=Field(max_length=30000)


@router.put('/projects/{slug}/draft')
def save_draft(slug:str,body:DraftWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    spec,_=project_visible(db,slug,user)
    if body.version!=project_version(spec):raise HTTPException(409,'Project changed; reload before saving this draft')
    draft=db.query(ProjectDraft).filter_by(user_id=user.id,project_slug=slug,milestone=body.milestone,version=body.version).first()
    if not draft:
        draft=ProjectDraft(user_id=user.id,project_slug=slug,milestone=body.milestone,version=body.version);db.add(draft)
    draft.artifact_text=body.artifact_text;draft.report=body.report;draft.updated_at=datetime.utcnow()
    db.commit();return dict(saved=True,updated_at=draft.updated_at)


class PromptExperimentWork(StrictBody):
    version:str=Field(min_length=1,max_length=64)
    baseline:str=Field(min_length=40,max_length=6000)
    candidate:str=Field(min_length=40,max_length=6000)


@router.post('/projects/{slug}/prompt-experiment',status_code=202)
def prompt_experiment(slug:str,body:PromptExperimentWork,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    spec,course=project_visible(db,slug,user)
    if slug!='team-prompt-evaluation':raise HTTPException(404,'This project does not define a prompt experiment')
    if body.version!=project_version(spec):raise HTTPException(409,'Reload the current project version')
    if db.query(EducationJob).filter(EducationJob.user_id==user.id,EducationJob.status.in_(['queued','running'])).count()>=5:
        raise HTTPException(429,'Wait for pending assessments before running more model experiments')
    record=ProjectExperiment(user_id=user.id,project_slug=slug,milestone=1,version=body.version,
                             artifact=dict(baseline=body.baseline,candidate=body.candidate),metrics=dict(status='queued'))
    db.add(record);db.flush()
    job=enqueue(db,key=f'prompt-experiment:{record.id}',kind='prompt_experiment',user_id=user.id,subject_id=record.id,version=body.version,
                payload=dict(baseline=body.baseline,candidate=body.candidate,course_id=course.id,title='Measured prompt comparison'))
    db.commit();return public_job(job)
