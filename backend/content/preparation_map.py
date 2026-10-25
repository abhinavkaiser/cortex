"""Explicit entry routes for every published course; stable lesson references."""
from content.learning_path import UNITS as BASIC
from content.advanced.lessons import ADVANCED_UNITS
from content.specializations.embeddings_finetuning import UNITS as EMBEDDINGS
from content.foundations.prerequisites import UNITS as FOUNDATIONS


def entry(statement,courses=(),lessons=(),beginner=False):
    return dict(statement=statement,course_slugs=list(courses),lesson_slugs=list(lessons),beginner=beginner)


COURSE_ENTRIES={
 'ai-fundamentals':entry('Start here. No previous AI, programming or mathematics course is required.',beginner=True),
 'python-for-ai':entry('Start here for programming. The course teaches the terminal, types, functions and software basics from the beginning.',beginner=True),
 'mathematics-for-ai':entry('Start here for mathematics. Work from numbers and units through vectors, matrices and gradients.',beginner=True),
 'probability-statistics-for-ai':entry('Begin with fractions, percentages and simple formulas. The linked mathematics lesson supplies that preparation.',lessons=['math-rates-algebra']),
 'ai-technical-bridge':entry('Combine the AI foundation with the Python, mathematics and statistics preparation courses before the bridge experiments.',courses=['ai-fundamentals','python-for-ai','mathematics-for-ai','probability-statistics-for-ai']),
 'ai-developer':entry('Prepare with the technical bridge and its linked beginner courses before production LLM engineering.',courses=['ai-technical-bridge']),
 'advanced-ml-research':entry('Prepare with the technical bridge. Lesson links identify the additional mathematics and experimental reasoning used by each research task.',courses=['ai-technical-bridge']),
 'embeddings-and-llm-fine-tuning':entry('Prepare with the technical bridge. No completed research project is required; specific maths and evaluation refreshers are linked within lessons.',courses=['ai-technical-bridge']),
 'ai-leader':entry('Begin with AI fundamentals, then review business rates and fair comparisons. Programming is not a prerequisite for this course.',courses=['ai-fundamentals'],lessons=['math-rates-algebra','stats-experiments-causality']),
 'ai-practitioner':entry('Begin with AI fundamentals and the linked rates/experiment lessons before comparing workflow outcomes. Programming is not required.',courses=['ai-fundamentals'],lessons=['math-rates-algebra','stats-experiments-causality']),
 'prompt-engineering-for-teams':entry('Begin with AI fundamentals and interpreting rates before measuring a team prompt library. Programming is not required.',courses=['ai-fundamentals'],lessons=['math-rates-algebra']),
 'building-ai-powered-products':entry('Begin with AI fundamentals, rates and fair experiment design before evaluating an AI product feature. A programming course is not required for these product decisions.',courses=['ai-fundamentals'],lessons=['math-rates-algebra','stats-experiments-causality']),
}

F=[u['slug'] for u in BASIC[:9]]
B=[u['slug'] for u in BASIC[9:]]
A=[u['slug'] for u in ADVANCED_UNITS]
E=[u['slug'] for u in EMBEDDINGS]
LESSON_REQUIREMENTS={
 F[0]:[],F[1]:[F[0]],F[2]:[F[1]],F[3]:[F[2]],F[4]:[F[1]],F[5]:[F[3]],F[6]:[F[5]],F[7]:[F[4]],F[8]:F[:8],
 B[0]:['python-files-json','python-debugging'],B[1]:[B[0],'python-api-contracts'],B[2]:[B[0],'math-vectors'],
 B[3]:[B[0],'stats-probability','stats-experiments-causality'],B[4]:[B[3],'math-optimization','stats-likelihood'],B[5]:B[:5],
 A[0]:[B[4],'python-functions','stats-likelihood'],A[1]:[A[0]],A[2]:[A[1],'stats-paired-comparisons'],
 A[3]:[A[0],A[2],'math-matrices'],A[4]:[A[2],F[6]],A[5]:[A[2],A[4]],
 E[0]:[B[2],'python-functions','math-vectors'],E[1]:[E[0]],E[2]:[E[1],'math-vectors'],E[3]:[E[2],'stats-paired-comparisons'],
 E[4]:[F[0],B[3],E[3]],E[5]:[E[4],'python-files-json'],E[6]:[E[5],F[0]],E[7]:[E[6],B[4],'math-gradients'],
 E[8]:[E[7],'math-matrices'],E[9]:[E[8],E[7]],E[10]:[E[7],E[8],E[5],'stats-paired-comparisons'],
 E[11]:[E[7],'stats-likelihood',E[10]],E[12]:[E[5],E[7],E[10]],E[13]:[E[9],E[10]],
 **{u['slug']:u['requires'] for u in FOUNDATIONS},
}
PATH_ORDER=[*F,*[u['slug'] for u in FOUNDATIONS],*B,*A,*E]
