"""Evals for the Daily Pulse pipeline -- scores a generated pulse before it
is allowed to flip from DRAFT to PUBLISHED (see models/daily_pulse.py's
PulseStatus). Two layers, deliberately kept separate:

1. Deterministic checks (cheap, no LLM call, run first) -- catch obviously
   broken output (empty fields, malformed quiz) without spending a token.
2. An LLM-as-judge rubric score (only runs if the deterministic checks
   pass) -- catches quality problems a regex can't, like a summary that's
   technically well-formed but shallow or factually disconnected from its
   sources.
"""

from dataclasses import dataclass

from app.services import claude_client

PUBLISH_THRESHOLD = 0.7

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "accuracy_score": {"type": "number", "description": "0-1: is the summary faithful to the source articles, no fabricated claims"},
        "clarity_score": {"type": "number", "description": "0-1: is the summary genuinely readable in ~2 minutes by the target track's audience"},
        "exercise_quality_score": {"type": "number", "description": "0-1: is the sandbox exercise concrete and actually doable, not vague busywork"},
        "quiz_quality_score": {"type": "number", "description": "0-1: does the quiz question test real understanding, with plausible (not silly) distractors"},
        "notes": {"type": "string", "description": "one or two sentences on the weakest part, if any"},
    },
    "required": ["accuracy_score", "clarity_score", "exercise_quality_score", "quiz_quality_score", "notes"],
}


@dataclass
class EvalResult:
    passed: bool
    score: float
    notes: str


def deterministic_checks(summary: str, sandbox_exercise: str, quiz_question: str, quiz_choices: list[str], quiz_correct_index: int) -> str | None:
    """Returns a failure reason string, or None if all checks pass."""
    if len(summary.strip()) < 100:
        return "summary is too short to be a real 2-minute read"
    if len(sandbox_exercise.strip()) < 40:
        return "sandbox exercise is too thin to be actionable"
    if len(quiz_choices) < 2:
        return "quiz needs at least 2 choices"
    if not (0 <= quiz_correct_index < len(quiz_choices)):
        return "quiz_correct_index out of range for quiz_choices"
    if len(set(quiz_choices)) != len(quiz_choices):
        return "quiz choices contain duplicates"
    return None


def score_with_llm_judge(source_articles_text: str, track_name: str, summary: str, sandbox_exercise: str, quiz_question: str, quiz_choices: list[str]) -> EvalResult:
    det_failure = deterministic_checks(summary, sandbox_exercise, quiz_question, quiz_choices, 0 if quiz_choices else -1)
    # Note: the caller passes the real quiz_correct_index into
    # deterministic_checks separately before calling this -- see
    # daily_pulse_agent.py's generate_and_evaluate for the actual call
    # order; this docstring-adjacent duplication is intentional so this
    # function can also be unit-tested with just the text fields.

    prompt = f"""You are grading a piece of AI-generated micro-learning content for factual accuracy and quality, not for style. The content was generated for the "{track_name}" learner track from the source articles below.

SOURCE ARTICLES:
{source_articles_text[:6000]}

GENERATED SUMMARY:
{summary}

GENERATED SANDBOX EXERCISE:
{sandbox_exercise}

GENERATED QUIZ:
Q: {quiz_question}
Choices: {quiz_choices}

Score each dimension 0.0-1.0. Be genuinely critical -- a summary that adds claims not supported by the source articles should score low on accuracy_score regardless of how well-written it reads."""

    result = claude_client.generate(prompt, temperature=0.0, response_schema=JUDGE_SCHEMA)
    import json

    parsed = json.loads(result.text)
    overall = (
        parsed["accuracy_score"] * 0.4
        + parsed["clarity_score"] * 0.2
        + parsed["exercise_quality_score"] * 0.2
        + parsed["quiz_quality_score"] * 0.2
    )
    return EvalResult(passed=overall >= PUBLISH_THRESHOLD, score=round(overall, 3), notes=parsed.get("notes", ""))
