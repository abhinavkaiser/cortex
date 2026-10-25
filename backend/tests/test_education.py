"""Contracts for project grading, durable jobs, safe amendments and real evidence."""
import copy
import json
from datetime import datetime,timedelta
from sqlalchemy.orm import sessionmaker
import pytest
from pydantic import ValidationError
from test_learning import setup,submission
from app.models import UserRole
from app.models.course import Course,Enrollment,Certificate
from app.models.learning import CurriculumSignal,PracticeAttempt,LearningUnit
from app.models.education import (EducationJob,EvidenceAttempt,GraderCalibration,LessonAmendment,
    ProjectSubmission,LearningEvent,LearningStudyAssignment)
from app.services.education_grading import assess,MODELS
from app.services.education_queue import enqueue,claim
from app.services.education_worker import run_one
from app.services.education_curriculum import build_amendment,fetch_evidence,effective_unit,enqueue_amendments
from app.services.education_outcomes import check_questions,course_project_passed
from app.services.learning import content_hash,ready
from app.services.project_benchmarks import benchmark,tool_benchmark,train_benchmark
from content.advanced.projects import PROJECTS,project_by_slug,project_version
from content.advanced.lessons import ADVANCED_UNITS
from content.advanced.evidence_checks import SKILLS,questions


def report():
    return ('I used the supplied source evidence and a fixed development split. I recorded the baseline and candidate configurations, '
            'inspected retrieval misses and excluded superseded or unauthorized documents. The reproducible command and code are included below. '
            'These synthetic results do not establish production performance; I would run a fresh representative evaluation and document uncertainty.')


def good_assessment(payload):
    passed=all(v is True for v in payload.get('benchmark',{}).get('checks',{}).values())
    return dict(score=100,passed=passed,status='graded',reviews=[],models=list(MODELS))


def complete_job(db):
    result=run_one(sessionmaker(bind=db.get_bind()),assessor=good_assessment,require_calibration=False)
    db.expire_all();return result


def baseline(client,user,skill='engineering'):
    bank=check_questions(user.id,skill,'baseline')
    response=client.post(f'/api/studio/checks/{skill}',json=dict(phase='baseline',answers=[q['correct_index'] for q in bank]))
    assert response.status_code==200


def project_setup(setup):
    client,db,user,other,course,lesson,unit=setup
    course.slug='ai-developer';db.commit()
    return client,db,user,other,course,lesson,unit,project_by_slug('grounded-support-engineer')


def test_rubric_requires_anchored_evidence_and_conservative_consensus():
    payload=dict(report=report(),rubric=[dict(id='criterion_1',description='Explain evidence')],benchmark=dict(checks={'safe':True}))
    def reviewer(instruction,data,model):
        return dict(criteria=[dict(id='criterion_1',score=4,evidence=data['report'][:70],feedback='The claim is supported; preserve the comparison and record its limits.')],summary='The supplied evidence supports this criterion.',next_steps=['Add an independent transfer case.'])
    assert assess(payload,reviewer=reviewer)['passed']
    def unanchored(*args):
        value=reviewer(*args);value['criteria'][0]['evidence']='This quote was never written by the learner.';return value
    with pytest.raises(ValueError):assess(payload,reviewer=unanchored)
    def disagrees(instruction,data,model):
        value=reviewer(instruction,data,model)
        if model==MODELS[0]:value['criteria'][0]['score']=0
        return value
    result=assess(payload,reviewer=disagrees)
    assert not result['passed'] and result['status']=='needs_review'
    payload['benchmark']['checks']['safe']=False
    assert not assess(payload,reviewer=reviewer)['passed']


@pytest.mark.parametrize('score',[4.0,'4',True,5,-1])
def test_model_score_shape_is_strict(score):
    def reviewer(*args):return dict(criteria=[dict(id='c',score=score,evidence='written evidence',feedback='A sufficiently concrete feedback explanation.')],summary='A sufficiently complete summary of the work.',next_steps=['Revise the evidence.'])
    with pytest.raises(ValidationError):assess(dict(report='written evidence',rubric=[dict(id='c')]),reviewer=reviewer)


def test_grading_is_durable_private_and_not_a_character_count_pass(setup):
    client,db,user,other,course,lesson,unit=setup
    result=client.post(f'/api/learning/lessons/{lesson.id}/practice',json=submission(unit)).json()
    assert not result['practice_complete'] and result['assessment']['status']=='queued'
    assert not ready(db,user.id,unit)
    job_id=result['assessment']['id']
    from app.main import app
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user]=lambda:other
    assert client.get(f'/api/studio/jobs/{job_id}').status_code==404
    assert client.get('/api/studio/history').json()==[]
    app.dependency_overrides[get_current_user]=lambda:user
    complete_job(db)
    assert ready(db,user.id,unit)
    assert client.get('/api/studio/history').json()[0]['assessment']['passed']


def test_worker_does_not_run_without_current_calibration(setup):
    client,db,user,other,course,lesson,unit=setup
    job=enqueue(db,key='test',kind='practice',user_id=user.id,subject_id=1,version='v1',payload={});db.commit()
    assert run_one(sessionmaker(bind=db.get_bind()),assessor=lambda data:pytest.fail('Must not call a grader')) is None
    db.expire_all();assert db.get(EducationJob,job.id).status=='queued'


def test_worker_failure_preserves_work_and_does_not_expose_provider_errors(setup):
    client,db,user,other,course,lesson,unit=setup
    result=client.post(f'/api/learning/lessons/{lesson.id}/practice',json=submission(unit)).json()
    def unavailable(data):raise RuntimeError('private-provider-diagnostic-must-not-leak')
    run_one(sessionmaker(bind=db.get_bind()),assessor=unavailable,require_calibration=False);db.expire_all()
    job=client.get(f"/api/studio/jobs/{result['assessment']['id']}").json()
    assert job['status']=='failed' and not job['passed']
    assert 'private-provider' not in json.dumps(job)
    assert db.query(PracticeAttempt).count()==1
    assert client.post(f"/api/studio/jobs/{job['id']}/retry").status_code==202


def test_interrupted_worker_job_is_recovered_with_a_bounded_retry(setup):
    _,db,user,*_=setup
    job=enqueue(db,key='interrupted',kind='practice',user_id=user.id,subject_id=1,version='v1',payload={})
    job.status='running';job.attempts=1;job.started_at=datetime.utcnow()-timedelta(minutes=20);db.commit()
    claimed=claim(db)
    assert claimed and claimed.id==job.id and claimed.attempts==2


def test_benchmarks_execute_configurations_and_reject_leakage():
    project=project_by_slug('grounded-support-engineer')
    result=benchmark(project,0,copy.deepcopy(project['milestones'][0]['starter']))
    assert all(result['checks'].values()) and result['metrics']['relevant_found']>0
    broken=copy.deepcopy(project['milestones'][0]['starter']);broken['enforce_access']=False
    assert not benchmark(project,0,broken)['checks']['unauthorized_document_filter']
    controls=copy.deepcopy(project['milestones'][1]['starter'])
    assert all(tool_benchmark(controls)['checks'].values())
    controls['idempotency']=False
    assert not tool_benchmark(controls)['checks']['retry']
    research=project_by_slug('ml-research-reproduction')['milestones'][0]['starter']
    result=train_benchmark(research)
    assert result['metrics']['test_count']==20 and result['metrics']['losses'][-1]['loss']<result['metrics']['losses'][0]['loss']
    leaky={**research,'use_leaky_feature':True}
    assert not train_benchmark(leaky)['checks']['no_label_leakage']
    with pytest.raises(ValueError):train_benchmark({**research,'epochs':10_000_000})
    preview=benchmark(project_by_slug('ml-research-reproduction'),0,research,preview=True)
    assert 'test_accuracy' not in preview['metrics']


def test_every_project_starter_is_valid_and_has_substantive_rubrics():
    assert len(PROJECTS)==6 and len(ADVANCED_UNITS)==6
    for project in PROJECTS:
        assert len(project['milestones'])==3
        for index,milestone in enumerate(project['milestones']):
            value=benchmark(project,index,copy.deepcopy(milestone['starter']))
            assert all(value['checks'].values())
            assert len(milestone['rubric'])==4 and len(milestone['task'])>=120


def test_project_milestones_and_objective_checks_cannot_be_skipped(setup):
    client,db,user,other,course,lesson,unit,project=project_setup(setup)
    body=dict(version=project_version(project),milestone=0,artifact=project['milestones'][0]['starter'],report=report())
    assert client.post(f"/api/studio/projects/{project['slug']}/submissions",json=body).status_code==409
    baseline(client,user)
    assert client.post(f"/api/studio/projects/{project['slug']}/submissions",json={**body,'milestone':1,'artifact':project['milestones'][1]['starter']}).status_code==409
    response=client.post(f"/api/studio/projects/{project['slug']}/experiment",json={key:value for key,value in body.items() if key!='report'})
    assert response.status_code==200
    response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=body)
    assert response.status_code==202 and not response.json()['assessment']['passed']
    complete_job(db)
    detail=client.get(f"/api/studio/projects/{project['slug']}").json()
    assert detail['milestones'][0]['passed'] and detail['milestones'][0]['experiments']
    assert not course_project_passed(db,user.id,course.slug)


def test_project_and_transfer_gate_new_certificates(setup):
    client,db,user,other,course,lesson,unit,project=project_setup(setup)
    db.add(Enrollment(user_id=user.id,course_id=course.id));db.commit()
    baseline(client,user)
    client.post(f'/api/learning/lessons/{lesson.id}/practice',json=submission(unit));complete_job(db)
    assert client.post('/api/users/lessons/complete',json={'lesson_id':lesson.id}).status_code==200
    assert db.query(Certificate).count()==0
    for index in range(3):
        response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=dict(version=project_version(project),milestone=index,artifact=project['milestones'][index]['starter'],report=report()))
        assert response.status_code==202;complete_job(db)
    assert db.query(Certificate).count()==0
    bank=check_questions(user.id,'engineering','transfer')
    result=client.post('/api/studio/checks/engineering',json=dict(phase='transfer',answers=[q['correct_index'] for q in bank]))
    assert result.status_code==200 and result.json()['score']==100
    assert course_project_passed(db,user.id,course.slug)
    assert db.query(Certificate).count()==1


def test_checks_are_private_parallel_and_preserve_original_scores(setup):
    client,db,user,other,*_=setup
    public=client.get('/api/studio/checks/analysis/baseline').json()
    assert len(public['questions'])==6 and 'correct_index' not in json.dumps(public)
    assert check_questions(user.id,'analysis','baseline')!=check_questions(other.id,'analysis','baseline')
    invalid=client.post('/api/studio/checks/analysis',json=dict(phase='baseline',answers=[True]*6))
    assert invalid.status_code==422
    baseline(client,user,'analysis')
    assert client.post('/api/studio/checks/analysis',json=dict(phase='baseline',answers=[0]*6)).status_code==409
    assert client.get('/api/studio/checks/analysis/transfer').status_code==409
    assert client.get('/api/studio/checks/analysis/retention').status_code==409
    assert db.query(EvidenceAttempt).filter_by(skill='analysis',phase='baseline').count()==1


def test_retention_opens_only_after_seven_days(setup):
    client,db,user,*_=setup
    baseline(client,user,'analysis')
    record=EvidenceAttempt(user_id=user.id,skill='analysis',phase='transfer',variant=1,answers=[0]*6,score=50,snapshot=dict(questions=[]))
    db.add(record);db.commit()
    assert client.get('/api/studio/checks/analysis/retention').status_code==409
    record.created_at=datetime.utcnow()-timedelta(days=8);db.commit()
    assert len(client.get('/api/studio/checks/analysis/retention').json()['questions'])==6


def test_no_fake_validation_and_opt_out_excludes_pilot_results(setup):
    client,db,user,other,*_=setup
    assert client.get('/api/studio/study/report').status_code==403
    assert not client.get('/api/studio/study').json()['consent']
    assert db.query(LearningStudyAssignment).count()==0
    baseline(client,user,'analysis')
    client.post('/api/studio/study',json=dict(consent=True))
    client.post('/api/studio/study',json=dict(consent=False))
    user.role=UserRole.ADMIN;db.commit()
    result=client.get('/api/studio/study/report').json()
    assert result['status']=='collecting_real_evidence'
    assert sum(group['enrolled'] for group in result['arms'].values())==0
    assert 'Insufficient' in result['conclusion']


def test_activity_is_wall_clock_bounded(setup):
    client,db,user,other,course,lesson,unit=setup
    client.post('/api/studio/activity',json=dict(lesson_id=lesson.id,seconds=60))
    row=db.query(LearningEvent).one();assert row.active_seconds==0
    row.last_seen_at=datetime.utcnow()-timedelta(seconds=10);db.commit()
    client.post('/api/studio/activity',json=dict(lesson_id=lesson.id,seconds=60));db.refresh(row)
    assert 10<=row.active_seconds<=11
    prior=row.active_seconds
    client.post('/api/studio/activity',json=dict(lesson_id=lesson.id,seconds=60));db.refresh(row)
    assert row.active_seconds<=prior+1


def test_evidence_checks_resist_obvious_answer_length_rules():
    for skill in SKILLS:
        for variant in range(3):
            bank=questions(skill,variant)
            assert len(bank)==6
            assert all(len(set(q['choices']))==4 for q in bank)
            for choose in (max,min):
                assert sum(choose(range(4),key=lambda i:len(q['choices'][i]))==q['correct_index'] for q in bank)<=3


def valid_amendment():
    return dict(title='A source-backed retrieval evaluation update',markdown=('The publisher reports a retrieval evaluation change. Compare the existing keyword baseline with a controlled candidate on the same queries. Keep source versions and access filters fixed, inspect failures and report limits. '*6),
                evidence=[dict(claim='The source reports a retrieval evaluation change.',quote='The new retrieval evaluation compares methods on the same fixed query set.')],
                question=dict(question='What should remain fixed when comparing retrieval methods?',choices=['The corpus and query set.','The preferred model brand.','Only the answer tone.','Only the report length.'],correct_index=0,feedback=['Correct: preserve the corpus and questions to compare methods.','A brand preference is not a fixed evaluation protocol.','Tone does not establish retrieval performance.','Report length does not define the comparison.']),
                reflection_prompt='Explain a controlled comparison and one limitation.',reference='Compare baseline and candidate on the same corpus and questions, preserve access controls and inspect case-level differences without extrapolating vendor results.',rubric='Defines a fixed comparison and distinguishes reported claims from measured evidence.')


def test_amendments_require_exact_source_support_and_independent_approval():
    data=valid_amendment()
    payload=dict(url='https://huggingface.co/blog/example',lesson_title='Retrieval',lesson_text='Compare retrieval approaches.',source_title='Evaluation update')
    source='The new retrieval evaluation compares methods on the same fixed query set. '+('Supporting article context. '*30)
    def writer(instruction,payload,model):
        if model==MODELS[1]:return data
        return dict(grounded=True,relevant=True,educational=True,question_correct=True,separates_reported_claims=True,ignores_embedded_instructions=True,reason='All claims are supported and the update teaches a controlled comparison.')
    assert build_amendment(payload,writer=writer,fetcher=lambda url:source)['approved']
    unsupported=copy.deepcopy(data);unsupported['evidence'][0]['quote']='This claim does not appear anywhere in the source article.'
    with pytest.raises(ValueError):build_amendment(payload,writer=lambda *args:unsupported,fetcher=lambda url:source)
    with pytest.raises(ValueError):fetch_evidence('http://127.0.0.1/admin')
    with pytest.raises(ValueError):fetch_evidence('https://example.org/unapproved')


def test_published_amendment_updates_teaching_and_invalidates_prior_practice(setup):
    client,db,user,other,course,lesson,unit=setup
    client.post(f'/api/learning/lessons/{lesson.id}/practice',json=submission(unit));complete_job(db)
    assert ready(db,user.id,unit)
    signal=CurriculumSignal(url='https://huggingface.co/blog/example',title='Retrieval evaluation',summary='A new benchmark',source='Test',published_at=datetime.utcnow(),lesson_slugs=[lesson.slug])
    db.add(signal);db.flush()
    job=enqueue(db,key='amendment-test',kind='curriculum',user_id=None,subject_id=lesson.id,version=unit.version,
                payload=dict(signal_id=signal.id,url=signal.url,source_title=signal.title,lesson_title=lesson.title,lesson_text=lesson.content_markdown,content_hash=content_hash(lesson),course_id=course.id))
    db.commit()
    result=dict(approved=True,amendment=valid_amendment(),review={},source_sha256='a'*64,source_url=signal.url,models=list(MODELS))
    run_one(sessionmaker(bind=db.get_bind()),builder=lambda data:result,require_calibration=False);db.expire_all()
    assert db.query(LessonAmendment).count()==1
    assert not ready(db,user.id,unit)
    detail=client.get(f'/api/learning/lessons/{lesson.id}').json()
    assert detail['version']!=unit.version and len(detail['exercise']['questions'])==3
    assert 'correct_index' not in json.dumps(detail['exercise'])
    text=client.get(f'/api/lessons/{lesson.id}').json()
    assert 'Course update:' in text['content_markdown']
    assert lesson.content_markdown=='Reviewed text'
    amendment=db.query(LessonAmendment).one()
    user.role=UserRole.INSTRUCTOR;db.commit()
    assert client.post(f'/api/studio/amendments/{amendment.id}/withdraw',json=dict(reason='The source needs additional context and should be withdrawn pending a corrected interpretation.')).status_code==200
    assert ready(db,user.id,unit)


def test_instructor_review_cannot_bypass_objective_failure(setup):
    client,db,user,other,course,lesson,unit=setup
    job=enqueue(db,key='appeal',kind='practice',user_id=other.id,subject_id=10,version='v',payload=dict(course_id=course.id,benchmark=dict(checks={'safe':False})))
    job.status='graded';job.result={};db.commit()
    body=dict(passed=True,score=90,explanation='I inspected the evidence and computations, including every criterion, and explain the decision here.')
    assert client.post(f'/api/studio/jobs/{job.id}/review',json=body).status_code in (403,404)
    user.role=UserRole.INSTRUCTOR;db.commit()
    assert client.post(f'/api/studio/jobs/{job.id}/review',json=body).status_code==422


def test_model_adapter_disables_tools_and_records_requested_model(monkeypatch):
    from types import SimpleNamespace
    from app.services import claude_client
    import os
    def process(args,**kwargs):
        assert args[1]=='exec' and '--ignore-user-config' in args
        assert args[args.index('--sandbox')+1]=='read-only'
        assert 'approval_policy="never"' in args and 'features.shell_tool=false' in args
        assert 'features.view_image=false' in args and 'web_search="disabled"' in args
        assert '--ephemeral' in args and '--ignore-rules' in args
        assert kwargs['cwd']!=os.getcwd()
        event=dict(type='item.completed',item=dict(type='agent_message',text='{"value":1}'))
        return SimpleNamespace(returncode=0,stdout=json.dumps(event),stderr='')
    monkeypatch.setattr(claude_client.subprocess,'run',process)
    result=claude_client._spawn_claude('Evidence only','sonnet',structured_envelope=True)
    assert result['model_ids']==['gpt-5.4'] and json.loads(result['text'])['value']==1
    assert claude_client._schema_example(dict(properties=dict(check=dict(type='boolean'))))['check'] is False


def test_subscription_runtime_rejects_tools_errors_and_unknown_models(monkeypatch):
    from types import SimpleNamespace
    from app.services import claude_client
    monkeypatch.setattr(claude_client.subprocess,'run',lambda *a,**k: SimpleNamespace(returncode=0,stdout=json.dumps(dict(type='item.started',item=dict(type='command_execution',command='cat /etc/passwd'))),stderr=''))
    with pytest.raises(RuntimeError,match='Unexpected tool use'):
        claude_client._spawn_claude('Untrusted work','sonnet')
    with pytest.raises(ValueError,match='Unsupported model'):
        claude_client._spawn_claude('Untrusted work','arbitrary-provider-model')
    monkeypatch.setattr(claude_client.subprocess,'run',lambda *a,**k: SimpleNamespace(returncode=1,stdout='',stderr='401 Authentication failure PRIVATE_ACCOUNT_DATA'))
    with pytest.raises(RuntimeError,match='authentication') as error:
        claude_client._spawn_claude('Work','sonnet')
    assert 'PRIVATE_ACCOUNT_DATA' not in str(error.value)


def test_daily_pulse_cannot_average_away_factual_failure(monkeypatch):
    from app.agents import evals
    from types import SimpleNamespace
    scores=dict(accuracy_score=.25,clarity_score=1,exercise_quality_score=1,quiz_quality_score=1,answer_key_correct=True,notes='Unsupported claim')
    def generate(prompt,**kwargs):
        assert 'Designated correct index: 1' in prompt
        return SimpleNamespace(text=json.dumps(scores))
    monkeypatch.setattr(evals.claude_client,'generate',generate)
    args=('Source facts','Developer','A sufficiently detailed factual summary. '*8,'A specific exercise with meaningful steps and source evidence.','Which response is supported by the source?',['First plausible answer','Second supported answer'],1)
    assert not evals.score_with_llm_judge(*args).passed
    scores['accuracy_score']=1;scores['answer_key_correct']=False
    assert not evals.score_with_llm_judge(*args).passed
    scores['answer_key_correct']=True
    assert evals.score_with_llm_judge(*args).passed
    scores['accuracy_score']=float('nan')
    assert not evals.score_with_llm_judge(*args).passed


def test_reassessment_requires_new_passing_work_and_keeps_original_score(setup):
    client,db,user,other,course,lesson,unit,project=project_setup(setup)
    baseline(client,user)
    for index in range(3):
        response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=dict(version=project_version(project),milestone=index,artifact=project['milestones'][index]['starter'],report=report()))
        assert response.status_code==202;complete_job(db)
    bank=check_questions(user.id,'engineering','transfer')
    wrong=[(q['correct_index']+1)%4 for q in bank]
    assert client.post('/api/studio/checks/engineering',json=dict(phase='transfer',answers=wrong)).json()['score']==0
    assert client.get('/api/studio/checks/engineering/reassessment').status_code==409
    response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=dict(version=project_version(project),milestone=2,artifact=project['milestones'][2]['starter'],report=report()+' I revised this final report after the transfer check.'))
    assert response.status_code==202;complete_job(db)
    check=client.get('/api/studio/checks/engineering/reassessment')
    assert check.status_code==200
    key=check.json()['record_phase'];bank=check_questions(user.id,'engineering',key)
    assert client.post('/api/studio/checks/engineering',json=dict(phase='reassessment',answers=[q['correct_index'] for q in bank])).status_code==200
    original=db.query(EvidenceAttempt).filter_by(user_id=user.id,skill='engineering',phase='transfer').one()
    assert original.score==0
    assert course_project_passed(db,user.id,course.slug)


def test_advanced_practice_does_not_reintroduce_length_cues():
    bank=[q for unit in ADVANCED_UNITS for q in unit['exercise']['questions']]
    for choose in (min,max):
        assert sum(choose(range(4),key=lambda i:len(q['choices'][i]))==q['correct_index'] for q in bank)<=len(bank)/2


def test_project_drafts_persist_without_triggering_grading_and_are_private(setup):
    client,db,user,other,course,lesson,unit,project=project_setup(setup)
    body=dict(version=project_version(project),milestone=0,artifact_text='{"unfinished":',report='An unfinished report that should survive navigation.')
    assert client.put(f"/api/studio/projects/{project['slug']}/draft",json=body).status_code==200
    detail=client.get(f"/api/studio/projects/{project['slug']}").json()
    assert detail['milestones'][0]['draft']['report']==body['report']
    assert db.query(EducationJob).count()==0
    from app.main import app
    from app.api.deps import get_current_user
    app.dependency_overrides[get_current_user]=lambda:other
    assert client.get(f"/api/studio/projects/{project['slug']}").json()['milestones'][0]['draft'] is None


def test_prompt_comparison_scores_real_predictions_not_claimed_counts():
    from app.services.prompt_experiments import CASES,run_experiment
    def runner(instruction,data,model):
        values=[dict(case_id=c['id'],**c['expected']) for c in CASES]
        if data['task_prompt']=='baseline':values[0]['order_id']='WRONG'
        return dict(predictions=values)
    result=run_experiment(dict(baseline='baseline',candidate='candidate'),runner=runner)
    assert result['metrics']['baseline_success']==5 and result['metrics']['candidate_success']==6
    assert result['metrics']['wins']==1 and result['metrics']['regressions']==0
    assert not result['passed'] and result['status']=='completed'


def test_prompt_milestone_cannot_pass_from_self_declared_success_flags(setup):
    client,db,user,other,course,lesson,unit=setup
    project=project_by_slug('team-prompt-evaluation');course.slug=project['course'];db.commit()
    baseline(client,user,'prompting')
    response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=dict(version=project_version(project),milestone=0,artifact=project['milestones'][0]['starter'],report=report()))
    assert response.status_code==202;complete_job(db)
    response=client.post(f"/api/studio/projects/{project['slug']}/submissions",json=dict(version=project_version(project),milestone=1,artifact=dict(baseline=[True]*6,candidate=[True]*6),report=report()))
    assert response.status_code==202 and response.json()['benchmark']['checks']['measured_prompt_run'] is False
    complete_job(db)
    assert not client.get(f"/api/studio/projects/{project['slug']}").json()['milestones'][1]['passed']


def test_instructors_cannot_self_approve_their_own_assessment(setup):
    client,db,user,other,course,lesson,unit=setup
    user.role=UserRole.INSTRUCTOR
    job=enqueue(db,key='self-review',kind='practice',user_id=user.id,subject_id=1,version='v',payload=dict(course_id=course.id,benchmark=dict(checks={'safe':True})))
    job.status='graded';job.result={};db.commit()
    response=client.post(f'/api/studio/jobs/{job.id}/review',json=dict(passed=True,score=100,explanation='I would like to approve my own work even though this does not provide an independent assessment.'))
    assert response.status_code==403
