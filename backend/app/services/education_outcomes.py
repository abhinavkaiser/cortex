"""Personal learning evidence and a prospectively defined opt-in pilot."""
import hashlib
import hmac
import random
from datetime import datetime,timedelta
from sqlalchemy import func
from app.core.config import get_settings
from app.models.education import (EducationJob,EvidenceAttempt,LearningEvent,LearningStudyAssignment,ProjectSubmission)
from app.models.learning import PracticeAttempt
from app.models.user import User
from content.advanced.evidence_checks import questions,SKILLS
from content.advanced.projects import project_by_slug,project_version,PROJECTS

PROTOCOL='lesson-order-pilot-v1'


def seeded(user_id,scope):
    digest=hmac.new(get_settings().jwt_secret.encode(),f'{PROTOCOL}:{user_id}:{scope}'.encode(),hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest,'big'))


def presentation(user_id):
    return 'practice_first' if seeded(user_id,'presentation').randrange(2)==0 else 'explanation_first'


def check_questions(user_id,skill,phase):
    variant=3+int(phase.split('_')[1]) if phase.startswith('reassessment_') else {'baseline':0,'transfer':1,'retention':2}[phase]
    bank=questions(skill,variant)
    rng=seeded(user_id,skill+':'+phase)
    rng.shuffle(bank)
    for q in bank:
        order=list(range(4));rng.shuffle(order)
        correct=order.index(q['correct_index'])
        q['choices']=[q['choices'][index] for index in order]
        q['correct_index']=correct
    return bank


def milestones_passed(db,user_id,project):
    for index in range(len(project['milestones'])):
        match=(db.query(ProjectSubmission).join(EducationJob,(EducationJob.subject_id==ProjectSubmission.id)&(EducationJob.kind=='project'))
               .filter(ProjectSubmission.user_id==user_id,ProjectSubmission.project_slug==project['slug'],ProjectSubmission.milestone==index,
                       ProjectSubmission.version==project_version(project),EducationJob.user_id==user_id,
                       EducationJob.status=='graded',EducationJob.passed.is_(True)).first())
        if not match:return False
    return True


def course_project_passed(db,user_id,course_slug):
    project=next((p for p in PROJECTS if p['course']==course_slug),None)
    if not project:return True
    transfer=db.query(EvidenceAttempt).filter_by(user_id=user_id,skill=project['skill'],phase='transfer').first()
    validated=db.query(EvidenceAttempt).filter(EvidenceAttempt.user_id==user_id,EvidenceAttempt.skill==project['skill'],EvidenceAttempt.phase!='baseline',EvidenceAttempt.score>=80).first()
    return milestones_passed(db,user_id,project) and validated is not None


def evidence_state(db,user_id,skill):
    rows={row.phase:row for row in db.query(EvidenceAttempt).filter_by(user_id=user_id,skill=skill).all()}
    baseline,transfer,retention=(rows.get(key) for key in ['baseline','transfer','retention'])
    due=transfer.created_at+timedelta(days=7) if transfer else None
    rechecks=[row for name,row in rows.items() if name.startswith('reassessment_')]
    return dict(skill=skill,reassessment_count=len(rechecks),reassessment_best=max((row.score for row in rechecks),default=None),baseline=baseline.score if baseline else None,transfer=transfer.score if transfer else None,
                retention=retention.score if retention else None,items_per_check=6,
                transfer_change_points=transfer.score-baseline.score if baseline and transfer else None,
                retention_due=due,retention_available=bool(due and due<=datetime.utcnow() and not retention),
                note='Six-item near-transfer checks are preliminary evidence. Project work adds separate evidence; this is not a standardized ability score.')


def outcomes(db,user_id):
    attempts=db.query(PracticeAttempt).filter_by(user_id=user_id).order_by(PracticeAttempt.id).all()
    first={}
    for attempt in attempts:first.setdefault((attempt.lesson_id,attempt.version),attempt)
    active=db.query(func.sum(LearningEvent.active_seconds)).filter_by(user_id=user_id).scalar() or 0
    days=db.query(func.count(func.distinct(LearningEvent.day))).filter_by(user_id=user_id).scalar() or 0
    return dict(evidence=[evidence_state(db,user_id,skill) for skill in SKILLS],
                engagement=dict(active_minutes=round(active/60,1),active_days=days,practice_attempts=len(attempts),
                                revisions=max(0,len(attempts)-len(first)),
                                first_attempt_decision_mean=round(sum(a.score for a in first.values())/len(first),1) if first else None,
                                note='Active time is bounded client-reported engagement, not proof of learning.'),
                written_work=dict(graded=db.query(EducationJob).filter_by(user_id=user_id,status='graded').filter(EducationJob.kind.in_(['practice','project'])).count(),
                                  passed=db.query(EducationJob).filter_by(user_id=user_id,status='graded',passed=True).filter(EducationJob.kind.in_(['practice','project'])).count()))


def study_status(db,user_id):
    assignment=db.query(LearningStudyAssignment).filter_by(user_id=user_id).first()
    return dict(protocol=PROTOCOL,consent=bool(assignment and assignment.consent),arm=presentation(user_id),
                primary_outcome='Seven-day retention on parallel six-item checks',
                comparison='Practice-first versus explanation-first; both receive the same content, feedback and projects.',
                pilot_target='At least 20 completed retention checks per arm for a descriptive pilot; not a universal power calculation.',
                privacy='Only opted-in aggregated scores and bounded engagement are included; written responses are not shared in cohort reports.',
                limitation='No learning-effect claim is made before real follow-up data; attrition, small samples and course revisions must be reported.')


def cohort_report(db):
    groups={arm:dict(enrolled=0,baseline=0,transfer=0,retention=0,retention_scores=[],paired_changes=[]) for arm in ['practice_first','explanation_first']}
    users=(db.query(LearningStudyAssignment,User).join(User,User.id==LearningStudyAssignment.user_id)
           .filter(LearningStudyAssignment.consent.is_(True),LearningStudyAssignment.protocol==PROTOCOL).all())
    for assignment,user in users:
        if user.email=='demo@cortex.ai' or user.role.value!='learner':continue
        if not assignment.consented_at: continue
        group=groups[assignment.arm];group['enrolled']+=1
        rows=(db.query(EvidenceAttempt).filter(EvidenceAttempt.user_id==user.id,EvidenceAttempt.created_at>=assignment.consented_at).all())
        for phase in ['baseline','transfer','retention']:
            if any(row.phase==phase for row in rows):group[phase]+=1
        # Average per person, not per attempt, so prolific learners do not dominate.
        retained=[row.score for row in rows if row.phase=='retention']
        if retained:group['retention_scores'].append(sum(retained)/len(retained))
        changes=[]
        for skill in SKILLS:
            pair={row.phase:row.score for row in rows if row.skill==skill}
            if 'baseline' in pair and 'transfer' in pair:changes.append(pair['transfer']-pair['baseline'])
        if changes:group['paired_changes'].append(sum(changes)/len(changes))
    ready=all(group['retention']>=20 for group in groups.values())
    report={}
    for arm,group in groups.items():
        count=len(group['retention_scores'])
        report[arm]=dict(enrolled=group['enrolled'],baseline_participants=group['baseline'],transfer_participants=group['transfer'],retention_participants=group['retention'],
                         retention_mean=round(sum(group['retention_scores'])/count,1) if count>=5 else None,
                         observed_paired_change_mean=round(sum(group['paired_changes'])/len(group['paired_changes']),1) if len(group['paired_changes'])>=5 else None,
                         missing_retention=max(0,group['enrolled']-group['retention']))
    return dict(protocol=PROTOCOL,status='descriptive_pilot_ready' if ready else 'collecting_real_evidence',arms=report,
                conclusion='Insufficient follow-up evidence to validate learning or engagement effects.' if not ready else 'Descriptive pilot data are available. Inspect attrition, uncertainty and revision exposure before making any causal claim.',
                note='Scores are not randomized-treatment effect estimates. The pilot is not powered to establish small effects; no fabricated student records are used.')
