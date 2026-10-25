"""Resolve published prerequisites and reject missing resources or dependency cycles."""
import hashlib,json,re
from sqlalchemy.orm import joinedload
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.preparation import PreparationProfile


def profile_hash(profile):
    values={key:getattr(profile,key) for key in ['statement','beginner','course_slugs','lesson_slugs']}
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()


def catalog_state(db):
    courses={c.slug:c for c in db.query(Course).filter_by(is_published=True).all()}
    lessons={l.slug:l for l in db.query(Lesson).join(Module).join(Course).filter(Course.is_published.is_(True)).options(joinedload(Lesson.module)).all()}
    rows=db.query(PreparationProfile).all()
    return courses,lessons,{p.course_id:p for p in rows if p.course_id},{p.lesson_id:p for p in rows if p.lesson_id}


def _audit(state):
    courses,lessons,course_profiles,lesson_profiles=state
    graph={**{'course:'+slug:[] for slug in courses},**{'lesson:'+slug:[] for slug in lessons}}
    errors=[]
    def links(profile,owner):
        if profile is None:
            errors.append('Preparation not declared: '+owner);return []
        if profile.beginner and (profile.course_slugs or profile.lesson_slugs):errors.append('Beginner entry has dependencies: '+owner)
        if profile.course_id and not profile.beginner and not (profile.course_slugs or profile.lesson_slugs):errors.append('Specify prerequisites or declare a beginner entry: '+owner)
        targets=['course:'+s for s in profile.course_slugs]+['lesson:'+s for s in profile.lesson_slugs]
        for target in targets:
            if target not in graph:errors.append('Unavailable published prerequisite for '+owner+': '+target)
        return [target for target in targets if target in graph]
    by_course={c.id:[] for c in courses.values()}
    for slug,lesson in lessons.items():
        by_course[lesson.module.course_id].append('lesson:'+slug)
        if not lesson.content_markdown.strip() and not lesson.content_blocks:errors.append('Empty published lesson: '+slug)
    for slug,course in courses.items():
        own=by_course[course.id]
        if not own:errors.append('Published course has no teaching: '+slug)
        graph['course:'+slug]=links(course_profiles.get(course.id),'course:'+slug)+own
    for slug,lesson in lessons.items():
        inherited=course_profiles.get(lesson.module.course_id)
        graph['lesson:'+slug]=links(lesson_profiles.get(lesson.id),'lesson:'+slug)
        if inherited:
            graph['lesson:'+slug]+=['course:'+s for s in inherited.course_slugs if s in courses]
            graph['lesson:'+slug]+=['lesson:'+s for s in inherited.lesson_slugs if s in lessons]
    cycles=[];colors={};stack=[]
    def visit(node):
        if colors.get(node)==1:
            cycle=stack[stack.index(node):]+[node]
            if cycle not in cycles:cycles.append(cycle)
            return
        if colors.get(node)==2:return
        colors[node]=1;stack.append(node)
        for target in dict.fromkeys(graph[node]):visit(target)
        stack.pop();colors[node]=2
    for node in graph:visit(node)
    return dict(verified=not errors and not cycles,courses=len(courses),lessons=len(lessons),errors=errors,cycles=cycles)


def audit(db):return _audit(catalog_state(db))


def require_ready(db):
    result=audit(db)
    if not result['verified']:
        problem=result['errors'][0] if result['errors'] else 'Circular prerequisite: '+' -> '.join(result['cycles'][0])
        raise ValueError(problem)
    return result


def public_preparation(db,*,course_id=None,lesson_id=None):
    state=catalog_state(db);courses,lessons,course_profiles,lesson_profiles=state
    profile=course_profiles.get(course_id) if course_id else lesson_profiles.get(lesson_id)
    if profile is None:return None
    profiles=[profile]
    if lesson_id:
        lesson=next((l for l in lessons.values() if l.id==lesson_id),None)
        inherited=course_profiles.get(lesson.module.course_id) if lesson else None
        if inherited:profiles.append(inherited)
    items=[];seen=set()
    for source in profiles:
        for kind,slugs,available in [('course',source.course_slugs,courses),('lesson',source.lesson_slugs,lessons)]:
            for slug in slugs:
                target=available.get(slug)
                if not target or (kind,slug) in seen:continue
                seen.add((kind,slug))
                items.append(dict(kind=kind,slug=slug,id=target.id,title=target.title,url='/dashboard/courses/'+slug if kind=='course' else '/dashboard/lessons/'+str(target.id)))
    return dict(statement=profile.statement,beginner=profile.beginner and not items,items=items,verified=_audit(state)['verified'])


def render_preparation(db,lesson,markdown,blocks):
    profile=db.query(PreparationProfile).filter_by(lesson_id=lesson.id).first()
    if not profile:return markdown,blocks
    pattern=r'(\*\*(?:Before you start|Prerequisites):\*\*\s*)[^\n]+'
    def replace(text):return re.sub(pattern,lambda m:m.group(1)+profile.statement,text,count=1)
    return replace(markdown),[{**block,'markdown':replace(block['markdown'])} if block.get('type')=='text' and isinstance(block.get('markdown'),str) else block for block in blocks]


def validate_targets(db,profile,owner_course_id):
    courses,lessons,_,_=catalog_state(db)
    if len(set(profile.course_slugs))!=len(profile.course_slugs) or len(set(profile.lesson_slugs))!=len(profile.lesson_slugs):raise ValueError('Select each prerequisite once')
    if profile.beginner and (profile.course_slugs or profile.lesson_slugs):raise ValueError('A beginner entry cannot also require prior coursework')
    if profile.course_id and not profile.beginner and not (profile.course_slugs or profile.lesson_slugs):raise ValueError('Select preparation or declare a beginner entry')
    for slug in profile.course_slugs:
        if slug not in courses or courses[slug].id==owner_course_id:raise ValueError('Choose another published prerequisite course')
    for slug in profile.lesson_slugs:
        if slug not in lessons:raise ValueError('Choose a published prerequisite lesson')
        if profile.course_id and lessons[slug].module.course_id==owner_course_id:raise ValueError('Course entry preparation cannot require its own lessons')
        if profile.lesson_id==lessons[slug].id:raise ValueError('A lesson cannot require itself')
