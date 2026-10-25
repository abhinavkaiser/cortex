"""Bounded server-side benchmarks. Never execute submitted code or shell commands."""
import json
import math
import random
import re
from pathlib import Path


def number(data, key, expected=None, low=0, high=10_000_000):
    value = data.get(key)
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid numeric field: ' + key)
    if expected is not None and not math.isclose(value, expected, abs_tol=1e-8):
        raise ValueError('Use the supplied base-case value for ' + key + '; discuss alternatives in your report')
    return float(value)


def require_flags(data, flags):
    return {name: data.get(name) is True for name in flags}


def retrieval_benchmark(config):
    if config.get('method') not in ('keyword', 'bm25') or type(config.get('k')) is not int or not 1 <= config['k'] <= 5:
        raise ValueError('Choose method keyword/bm25 and integer k between 1 and 5')
    docs = json.loads((Path(__file__).resolve().parents[2] / 'content/labs/documents.json').read_text())
    docs.append(dict(id='private-invoice',text='Customer invoice secret account balance billing invoice',current=True,private=True))
    stop = {'a','an','the','is','are','what','how','do','i','of','to','for','and','in','on','can'}
    def terms(text): return [t for t in re.findall('[a-z]+',text.lower()) if t not in stop]
    def rank(query, private=False):
        eligible = [d for d in docs if (not config.get('current_only') or d['current']) and (private or not config.get('enforce_access') or not d.get('private'))]
        query_terms = terms(query)
        mean = sum(len(terms(d['text'])) for d in eligible) / max(len(eligible),1)
        scored = []
        for d in eligible:
            words = terms(d['text'])
            score = 0
            for term in query_terms:
                frequency = words.count(term)
                if config['method']=='keyword': score += bool(frequency)
                elif frequency:
                    df = sum(term in terms(item['text']) for item in eligible)
                    idf = math.log(1 + (len(eligible)-df+.5)/(df+.5))
                    score += idf * frequency * 2.2 / (frequency + 1.2*(.25+.75*len(words)/max(mean,1)))
            if score > 0: scored.append((score,d['id']))
        return [key for _,key in sorted(scored,reverse=True)[:config['k']]]
    cases = [('current returns policy',['returns-current']), ('damaged goods supervisor',['damage']),
             ('invoice download account',['invoice','access']), ('subscription renewal cancellation',['cancellation']),
             ('shop closed Sunday',['hours']), ('shipping delivery five pounds',['delivery'])]
    hits = required = 0
    for query,relevant in cases:
        found=rank(query);hits+=len(set(found)&set(relevant));required+=len(relevant)
    checks=dict(current_source_filter=config.get('current_only') is True,
                unauthorized_document_filter='private-invoice' not in rank('customer invoice secret account'),
                minimum_evidence_recall=hits/required >= .7)
    return dict(checks=checks, metrics=dict(relevant_found=hits,relevant_total=required,recall=round(hits/required,4),
                test_cases=len(cases),method=config['method'],k=config['k']),
                scope='Synthetic held-out configuration benchmark; submitted Python is reviewed, not executed.')


def train_benchmark(config):
    rate=number(config,'learning_rate',low=.001,high=1)
    epochs=int(number(config,'epochs',low=20,high=500))
    if type(config.get('epochs')) is not int: raise ValueError('epochs must be an integer')
    regularization=number(config,'regularization',low=0,high=1)
    rng=random.Random(4826)
    rows=[]
    for _ in range(96):
        x=[rng.uniform(-2,2),rng.uniform(-2,2)]
        y=int(1.4*x[0]-.8*x[1]+rng.gauss(0,.3)>.2)
        rows.append((x,y))
    train,validation,test=rows[:56],rows[56:76],rows[76:]
    mean=[sum(x[j] for x,_ in train)/len(train) for j in range(2)]
    scale=[math.sqrt(sum((x[j]-mean[j])**2 for x,_ in train)/len(train)) or 1 for j in range(2)]
    def standard(x):return [(x[j]-mean[j])/scale[j] for j in range(2)]
    weights=[0.,0.];bias=0.
    def probability(x):
        z=max(-40,min(40,sum(w*v for w,v in zip(weights,standard(x)))+bias))
        return 1/(1+math.exp(-z))
    for _ in range(epochs):
        dw=[0.,0.];db=0.
        for x,y in train:
            error=probability(x)-y;norm=standard(x)
            for j in range(2):dw[j]+=error*norm[j]
            db+=error
        for j in range(2):weights[j]-=rate*(dw[j]/len(train)+regularization*weights[j])
        bias-=rate*db/len(train)
    def accuracy(data):return sum((probability(x)>=.5)==bool(y) for x,y in data)/len(data)
    metrics=dict(train_count=len(train),validation_count=len(validation),test_count=len(test),
                 validation_accuracy=accuracy(validation),test_accuracy=accuracy(test),
                 majority_test_accuracy=max(sum(y for _,y in test),sum(1-y for _,y in test))/len(test),
                 weights=[round(w,5) for w in weights],bias=round(bias,5),seed=4826)
    return dict(checks=dict(no_label_leakage=config.get('use_leaky_feature') is False,
                           heldout_accuracy=metrics['test_accuracy']>=.75),metrics=metrics,
                scope='Bounded logistic-regression configuration on synthetic data; not a real-world model-quality estimate.')


def benchmark(project, milestone, data):
    if not isinstance(data,dict) or len(json.dumps(data))>8000:raise ValueError('Artifact must be a JSON object under 8,000 characters')
    slug=project['slug']
    if slug=='grounded-support-engineer':
        if milestone==0:return retrieval_benchmark(data)
        if milestone==1:return dict(checks=require_flags(data,['require_approval','validate_amount','enforce_total','idempotency']),metrics=dict(adversarial_case_families=4),scope='Executor policy checks; code implementation is separately reviewed.')
        values={k:number(data,k,expected=v) for k,v in project['milestones'][2]['starter'].items()}
        daily=values['requests_per_day']*(values['input_tokens']*values['input_per_million']+values['output_tokens']*values['output_per_million'])/1_000_000
        return dict(checks=dict(within_synthetic_budget=daily<=40),metrics=dict(daily_variable_cost=round(daily,2)),scope='Synthetic prices; excludes infrastructure and review costs.')
    if slug=='operations-workflow':
        if milestone==0:
            for k,v in project['milestones'][0]['starter'].items():number(data,k,expected=v)
            return dict(checks=dict(base_case=True),metrics=dict(before_rate=.1,after_rate=.06,percentage_point_change=-4,count_change_percent=20),scope='Observed rates, not causal evidence.')
        if milestone==1:
            for k,v in project['milestones'][1]['starter'].items():number(data,k,expected=v)
            saved=data['manual_minutes']-data['draft_minutes']-data['review_minutes']-data['correction_minutes']
            return dict(checks=dict(net_time_positive=saved>0),metrics=dict(minutes_saved=saved,weekly_capacity_value=saved*data['reports']/60*data['hourly_rate']),scope='Hypothetical released capacity, not necessarily cash savings.')
        return dict(checks=require_flags(data,['block_missing_denominator','reject_unapproved_source','require_review']),metrics={},scope='Workflow control contract; rubric checks the evidence and usability.')
    if slug=='enterprise-ai-playbook':
        if milestone==0:
            for k,v in project['milestones'][0]['starter'].items():number(data,k,expected=v)
            capacity=data['claims']*data['eligibility']*data['adoption']*data['minutes_saved']/60*data['hourly_rate']
            return dict(checks=dict(base_case=True),metrics=dict(annual_capacity_value=round(capacity,2)),scope='Conditional scenario, not measured return on investment.')
        budget=1_200_000 if milestone==1 else 900_000
        values={k:number(data,k) for k in ['technology','data','change','governance','budget']}
        return dict(checks=dict(budget_reconciles=values['budget']==budget and sum(values[k] for k in ['technology','data','change','governance'])==budget,
                                controls_funded=values['governance']>=100000,delivery_and_change_funded=all(values[k]>0 for k in ['technology','data','change'])),
                    metrics=dict(allocated=sum(values[k] for k in ['technology','data','change','governance']),budget=budget),scope='Multiple allocations can be defensible; rubric judges the rationale.')
    if slug=='team-prompt-evaluation':
        if milestone==0:
            return dict(checks=dict(missing_not_invented=data.get('missing_is_null') is True,
                                    categories=data.get('allow_categories')==['refund','delivery','account'],
                                    source_not_instruction=data.get('source_is_data') is True),metrics={},scope='Extraction contract; include actual prompt and outputs for review.')
        if milestone==1:
            a,b=data.get('baseline'),data.get('candidate')
            if not isinstance(a,list) or not isinstance(b,list) or len(a)!=6 or len(b)!=6 or any(type(x)is not bool for x in a+b):raise ValueError('Provide six boolean outcomes for each version')
            return dict(checks=dict(paired_cases=True),metrics=dict(baseline_success=sum(a),candidate_success=sum(b),cases=6,wins=sum(not x and y for x,y in zip(a,b)),regressions=sum(x and not y for x,y in zip(a,b))),scope='Submitted development observations; implementation evidence is reviewed and transfer is tested separately.')
        return dict(checks=require_flags(data,['versioned','owner_assigned','regression_gate','rollback']),metrics={},scope='Maintenance contract; grader checks the actual playbook.')
    if slug=='ai-product-launch':
        if milestone==0:
            for k,v in project['milestones'][0]['starter'].items():number(data,k,expected=v)
            return dict(checks=dict(base_case=True),metrics=dict(control_rate=.8,candidate_rate=.86,observed_difference_points=6),scope='Observed small-sample difference; significance and allocation are not established.')
        flags=['show_sources','allow_correction','explicit_approval','abstain_without_evidence'] if milestone==1 else ['canary','kill_switch','quality_monitor']
        checks=require_flags(data,flags)
        if milestone==2:checks['pricing_not_claimed_validated']=data.get('pricing_validated') is False
        return dict(checks=checks,metrics={},scope='Product control contract; substantive design and evidence are rubric-graded.')
    if slug=='ml-research-reproduction':
        if milestone<2:return train_benchmark(data)
        return dict(checks=require_flags(data,['protocol_recorded','heldout_separate','limitations_reported','primary_source']),metrics={},scope='Research protocol contract; two-model review checks the reported evidence.')
    raise ValueError('Unknown project')
