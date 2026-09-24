"""Backs the hand-built interactive explainer pages under /dashboard/explore
(e.g. "What a Language Model Actually Does") -- deliberately separate from
the lesson content-block pipeline (app/agents/lesson_blocks.py). Those
lessons are AI-generated once and stored; this route serves genuinely live
data for a bespoke, hand-authored page, in the spirit of poloclub's
WebSHAP/Transformer Explainer: real computed output, not fabricated
numbers presented as if they were model internals.

Real, already-existing local capabilities, reused here rather than faked:
  - claude_client.embed() -- real local sentence-transformers embeddings,
    no network call, no API key.
  - claude_client.generate() -- the real local Claude CLI subscription,
    same one every other feature in this app runs on.

Client-side tokenization (a real GPT-style BPE tokenizer, via the
`gpt-tokenizer` npm package) lives entirely in the frontend -- no backend
round trip needed for that part, and no server-side fabrication either.
"""

import ast
import re

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services import claude_client

router = APIRouter(prefix="/api/explore", tags=["explore"])


class EmbedRequest(BaseModel):
    items: list[str] = Field(min_length=2, max_length=12)


class EmbedPoint(BaseModel):
    label: str
    x: float
    y: float


class EmbedResponse(BaseModel):
    points: list[EmbedPoint]
    closest_pair: tuple[int, int]
    closest_similarity: float
    farthest_pair: tuple[int, int]
    farthest_similarity: float


@router.post("/embed", response_model=EmbedResponse)
def embed_words(body: EmbedRequest, user: User = Depends(get_current_user)):
    """Real embeddings for 2-12 short phrases, projected to 2D for plotting.

    PCA via numpy SVD on the *actual* embedding vectors -- not a fabricated
    layout. Cosine similarity is computed on the full-dimensional vectors
    (not the lossy 2D projection) so "closest pair" reflects real semantic
    proximity, and the 2D plot is presented as an approximation of that,
    which is what it genuinely is.
    """
    items = [i.strip() for i in body.items if i.strip()][:12]
    vectors = np.array([claude_client.embed(text) for text in items])

    centered = vectors - vectors.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T  # project onto the top 2 principal components

    # normalize embeddings are already unit-norm (claude_client.embed sets
    # normalize_embeddings=True), so the dot product IS the cosine similarity
    sim = vectors @ vectors.T
    n = len(items)
    best_i, best_j, best_sim = 0, 1, -2.0
    worst_i, worst_j, worst_sim = 0, 1, 2.0
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] > best_sim:
                best_i, best_j, best_sim = i, j, float(sim[i, j])
            if sim[i, j] < worst_sim:
                worst_i, worst_j, worst_sim = i, j, float(sim[i, j])

    return EmbedResponse(
        points=[EmbedPoint(label=items[k], x=float(coords[k, 0]), y=float(coords[k, 1])) for k in range(n)],
        closest_pair=(best_i, best_j),
        closest_similarity=best_sim,
        farthest_pair=(worst_i, worst_j),
        farthest_similarity=worst_sim,
    )


class CompleteRequest(BaseModel):
    prefix: str = Field(min_length=1, max_length=300)


class CompleteResponse(BaseModel):
    completion: str


_COMPLETE_SYSTEM_PROMPT = (
    "You are simulating next-token prediction for an educational demo. Continue the user's text "
    "naturally, as if you were the very next words a language model would generate. Reply with ONLY "
    "the continuation (no restating their text, no quotes, no explanation) -- 3 to 12 words, stopping "
    "at a natural phrase or sentence boundary."
)


@router.post("/complete", response_model=CompleteResponse)
def complete_text(body: CompleteRequest, user: User = Depends(get_current_user)):
    """A real live completion from the local Claude subscription, framed
    for the "predicting the next token" demo. Honest framing matters here:
    this shows real model output, not real logits/probabilities -- the CLI
    doesn't expose those, and the page copy says so rather than inventing
    percentages that would look precise but be fake."""
    result = claude_client.generate(body.prefix, model=None, system_prompt_override=_COMPLETE_SYSTEM_PROMPT, max_output_tokens=40)
    return CompleteResponse(completion=result.text.strip())


# ---------------------------------------------------------------------------
# RAG demo: a small, clearly-fictional "company handbook" (labeled as such to
# the reader) plus real embedding-similarity retrieval over it -- the exact
# same mechanism as /embed above, reused for its real purpose this time. The
# "grounded vs ungrounded" comparison is two real, live claude_client.generate()
# calls, not a scripted before/after.
# ---------------------------------------------------------------------------

DOCS = [
    "PTO policy: Full-time employees accrue 15 days of paid time off per year, capped at 30 days banked. Unused days beyond the cap are forfeited each January 1st.",
    "Expense policy: Meals under $75 do not require a receipt. Expenses over $75 require an itemized receipt submitted within 30 days.",
    "Remote work policy: Employees may work remotely up to 3 days per week without manager approval; more requires a written exception from their manager.",
    "Security policy: All company laptops must have disk encryption enabled and screen lock set to 5 minutes or less of inactivity.",
    "Parental leave policy: Primary caregivers receive 16 weeks of paid leave; secondary caregivers receive 6 weeks, both usable within 12 months of the qualifying event.",
    "Travel policy: Domestic flights must be booked at least 14 days in advance except for approved emergency travel, which requires VP sign-off after the fact.",
]

_doc_vectors_cache: list[list[float]] | None = None


def _doc_vectors() -> np.ndarray:
    global _doc_vectors_cache
    if _doc_vectors_cache is None:
        _doc_vectors_cache = [claude_client.embed(d) for d in DOCS]
    return np.array(_doc_vectors_cache)


def _retrieve(query: str, k: int = 2) -> list[tuple[str, float]]:
    q = np.array(claude_client.embed(query))
    vecs = _doc_vectors()
    sims = vecs @ q  # unit-norm vectors -> dot product is cosine similarity
    order = np.argsort(-sims)[:k]
    return [(DOCS[i], float(sims[i])) for i in order]


class RagRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)


class RagResult(BaseModel):
    text: str
    similarity: float


class RagResponse(BaseModel):
    retrieved: list[RagResult]
    ungrounded_answer: str
    grounded_answer: str


_UNGROUNDED_SYSTEM = (
    "Answer the user's question using only general world knowledge. You have no access to any specific "
    "company's actual policies. If the question asks about a specific company's numbers or rules, say plainly "
    "that you don't have access to that company's policy rather than guessing a number. Keep it to 2 sentences."
)
_GROUNDED_SYSTEM = (
    "Answer the user's question using ONLY the provided policy excerpt below -- do not use outside knowledge. "
    "If the excerpt doesn't actually answer the question, say so. Keep it to 2 sentences.\n\nPolicy excerpt:\n{context}"
)


@router.post("/rag", response_model=RagResponse)
def rag_demo(body: RagRequest, user: User = Depends(get_current_user)):
    """Real retrieval (embedding similarity over a small fictional doc set)
    feeding a real generation call, run side by side against the same
    question with no retrieval at all -- both calls are live, not canned."""
    retrieved = _retrieve(body.question, k=2)
    context = "\n".join(text for text, _ in retrieved)

    ungrounded = claude_client.generate(body.question, system_prompt_override=_UNGROUNDED_SYSTEM, max_output_tokens=100)
    grounded = claude_client.generate(body.question, system_prompt_override=_GROUNDED_SYSTEM.format(context=context), max_output_tokens=100)

    return RagResponse(
        retrieved=[RagResult(text=t, similarity=s) for t, s in retrieved],
        ungrounded_answer=ungrounded.text.strip(),
        grounded_answer=grounded.text.strip(),
    )


# ---------------------------------------------------------------------------
# Agent demo: a small, real ReAct-style loop. The model picks a tool in
# plain-text turns, the backend actually executes that tool (a whitelisted,
# eval-free arithmetic evaluator; or the same retrieval as the RAG demo
# above), feeds the real result back in, and repeats -- capped at a few
# steps. No fabricated trace: every step in the response is something that
# genuinely happened during this request.
# ---------------------------------------------------------------------------

_AGENT_SYSTEM = """You are an agent that solves a goal step by step using tools. You have exactly two tools:

- calculator: evaluates a pure arithmetic expression (numbers, + - * / ( ) only, no words) and returns the number.
- lookup_policy: searches a small company handbook and returns the most relevant excerpt(s) for a text query.

At every turn, respond with ONLY one of these two forms, nothing else -- no extra commentary:

TOOL: calculator
INPUT: <arithmetic expression>

TOOL: lookup_policy
INPUT: <search query>

FINAL: <your answer to the goal, using the results you've gathered so far>

Use FINAL as soon as you have enough information -- don't call tools you don't need. If you already have everything
required to answer, go straight to FINAL on your first turn."""

_TOOL_RE = re.compile(r"TOOL:\s*(calculator|lookup_policy)\s*\nINPUT:\s*(.+)", re.IGNORECASE)
_FINAL_RE = re.compile(r"FINAL:\s*(.+)", re.IGNORECASE | re.DOTALL)

_SAFE_ARITHMETIC_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)


def _safe_arithmetic_eval(expr: str) -> float:
    """A whitelisted-AST evaluator, not eval() -- only numeric literals and
    +-*/ unary/binary ops are accepted; anything else (names, calls,
    attribute access, subscripts) raises before any evaluation happens."""
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_ARITHMETIC_NODES):
            raise ValueError(f"disallowed expression: {expr!r}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(f"disallowed constant: {expr!r}")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
        if isinstance(node, ast.UnaryOp):
            val = _eval(node.operand)
            return -val if isinstance(node.op, ast.USub) else val
        raise ValueError(f"disallowed expression: {expr!r}")

    return _eval(tree)


class AgentRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=300)


class AgentStep(BaseModel):
    thought_raw: str
    tool: str | None
    tool_input: str | None
    observation: str | None


class AgentResponse(BaseModel):
    steps: list[AgentStep]
    final_answer: str


@router.post("/agent", response_model=AgentResponse)
def agent_demo(body: AgentRequest, user: User = Depends(get_current_user)):
    max_steps = 4
    transcript = f"Goal: {body.goal}"
    steps: list[AgentStep] = []

    for step_num in range(max_steps):
        forced_final = step_num == max_steps - 1
        prompt = transcript + ("\n\nYou must respond with FINAL now -- no more tool calls." if forced_final else "")
        result = claude_client.generate(prompt, system_prompt_override=_AGENT_SYSTEM, max_output_tokens=200)
        raw = result.text.strip()

        final_match = _FINAL_RE.search(raw)
        tool_match = _TOOL_RE.search(raw)

        if final_match and not (tool_match and tool_match.start() < final_match.start()):
            answer = final_match.group(1).strip()
            steps.append(AgentStep(thought_raw=raw, tool=None, tool_input=None, observation=None))
            return AgentResponse(steps=steps, final_answer=answer)

        if tool_match and not forced_final:
            tool, tool_input = tool_match.group(1).lower(), tool_match.group(2).strip()
            try:
                if tool == "calculator":
                    observation = str(_safe_arithmetic_eval(tool_input))
                else:
                    hits = _retrieve(tool_input, k=1)
                    observation = hits[0][0] if hits else "No matching policy found."
            except Exception as err:  # noqa: BLE001 -- a bad tool call is a real observation to feed back, not a crash
                observation = f"Tool error: {err}"

            steps.append(AgentStep(thought_raw=raw, tool=tool, tool_input=tool_input, observation=observation))
            transcript += f"\n\nTOOL: {tool}\nINPUT: {tool_input}\nOBSERVATION: {observation}"
            continue

        # model didn't follow the protocol -- treat its raw reply as the answer rather than crashing the demo
        steps.append(AgentStep(thought_raw=raw, tool=None, tool_input=None, observation=None))
        return AgentResponse(steps=steps, final_answer=raw)

    raise HTTPException(500, "Agent did not reach a final answer within the step limit.")
