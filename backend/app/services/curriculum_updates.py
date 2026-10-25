"""Source-backed lesson updates. No model writes canonical teaching content.

Headlines are signals for investigation, not verified course amendments. Fetch
only fixed configured feeds; links are never fetched or executed from articles.
"""
import calendar
import html
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.models.learning import CurriculumRefresh, CurriculumSignal

FEEDS = [
    ("Hugging Face blog", "https://huggingface.co/blog/feed.xml"),
    ("OpenAI announcements", "https://openai.com/news/rss.xml"),
    ("Google Research", "https://research.google/blog/rss/"),
]
TOPICS = {
    "what-is-a-language-model": ["language model", "transformer", "pretraining", "reasoning"],
    "ai-risk-and-limitations": ["hallucination", "grounding", "evaluation", "benchmark"],
    "privacy-confidentiality-what-not-to-paste": ["privacy", "security", "injection", "safety"],
    "bridge-vectors-and-retrieval": ["retrieval", "embedding", "rag", "search"],
    "bridge-optimization-and-neural-networks": ["training", "optimization", "fine-tuning", "neural"],
    "bridge-evaluation-and-experiments": ["evaluation", "benchmark", "reliability", "eval"],
    "bridge-http-json-and-validation": ["tool", "agent", "structured", "api"],
    "advanced-training-protocol": ["training", "optimization", "gradient", "classifier"],
    "advanced-generalization": ["generalization", "leakage", "robustness", "distribution shift"],
    "advanced-experimental-design": ["evaluation", "benchmark", "ablation", "reproducibility"],
    "advanced-representation-and-adaptation": ["adapter", "lora", "embedding", "fine-tuning"],
    "advanced-multimodal-evaluation": ["multimodal", "vision", "image", "audio", "video"],
    "advanced-paper-reproduction": ["research", "paper", "reproduction", "benchmark"],
    "embedding-representations": ["embedding", "representation", "semantic search"],
    "embedding-ingestion-chunking": ["chunking", "parsing", "retrieval"],
    "embedding-vector-indexes": ["vector", "index", "hybrid search", "rerank"],
    "embedding-evaluation-adaptation": ["embedding", "retrieval evaluation", "contrastive"],
    "llm-adaptation-strategy": ["fine-tuning", "adaptation", "pretraining"],
    "llm-training-data": ["dataset", "synthetic data", "contamination"],
    "llm-chat-templates-masking": ["chat template", "tokenization", "loss masking"],
    "llm-supervised-training": ["supervised fine-tuning", "sft", "training"],
    "llm-lora-adapters": ["lora", "adapter", "low-rank"],
    "llm-qlora-memory": ["qlora", "quantization", "quantized"],
    "llm-finetuning-evaluation": ["evaluation", "benchmark", "regression"],
    "llm-preference-optimization": ["dpo", "preference", "reward model"],
    "llm-distillation": ["distillation", "teacher", "student model"],
    "llm-adapter-deployment": ["inference", "serving", "deployment"],
    "python-api-contracts": ["api", "tool calling", "structured output"],
    "python-environments": ["dependency", "reproducibility"],
    "math-matrices": ["low-rank", "lora"],
    "math-gradients": ["gradient", "backpropagation"],
    "math-optimization": ["optimizer", "optimization"],
    "stats-likelihood": ["cross-entropy", "likelihood"],
    "stats-experiments-causality": ["experiment", "causal", "a/b"],
    "stats-paired-comparisons": ["benchmark", "evaluation"],
}


def plain(text):
    return html.unescape(re.sub(r'<[^>]+>', ' ', text or '')).strip()


def ingest(db: Session, *, now=None, feeds=FEEDS, fetch=None):
    now = now or datetime.utcnow()
    added = 0
    errors = []
    pending = {}
    checked_sources = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": "CortexLearning/1.0"}) as client:
        get = fetch or client.get
        for source, feed_url in feeds:
            try:
                response = get(feed_url)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                if not parsed.entries:
                    raise ValueError('Feed has no entries')
                for entry in parsed.entries[:30]:
                    timestamp = entry.get('published_parsed') or entry.get('updated_parsed')
                    if not timestamp:
                        continue
                    published = datetime.utcfromtimestamp(calendar.timegm(timestamp))
                    if published < now - timedelta(days=30) or published > now + timedelta(minutes=10):
                        continue
                    url = urlsplit(entry.get('link', ''))
                    if url.scheme != 'https' or not url.hostname or url.username or url.password:
                        continue
                    canonical = urlunsplit((url.scheme, url.netloc, url.path, url.query, ''))
                    if len(canonical) > 2000 or canonical in pending:
                        continue
                    title = plain(entry.get('title', ''))[:300]
                    summary = plain(entry.get('summary', ''))[:1200]
                    text = (title + ' ' + summary).lower()
                    slugs = [slug for slug, words in TOPICS.items() if any(re.search(r'\b' + re.escape(w) + r'(?:s)?\b', text) for w in words)]
                    if not title or not slugs:
                        continue
                    pending[canonical] = dict(url=canonical, title=title, summary=summary, source=source,
                                              published_at=published, fetched_at=now, lesson_slugs=slugs)
                checked_sources.append(source)
            except (httpx.HTTPError, ValueError, OverflowError) as error:
                # Report source and error type, never raw response bodies or URLs with credentials.
                errors.append(dict(source=source, error=type(error).__name__))
    # Network requests finish before acquiring SQLite's write lock.
    for url, values in pending.items():
        if not db.query(CurriculumSignal.id).filter_by(url=url).first():
            db.add(CurriculumSignal(**values))
            db.flush()
            added += 1
    result = dict(added=added, errors=errors, checked_sources=checked_sources, checked_at=now.isoformat())
    status = db.get(CurriculumRefresh, 1)
    if status is None:
        status = CurriculumRefresh(id=1)
        db.add(status)
    status.checked_at, status.result = now, result
    db.commit()
    return result
