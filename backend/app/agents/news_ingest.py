"""Fetches and normalizes AI news from the configured RSS feeds. Pure
ingestion -- no LLM calls here, so this stage is cheap to run/retry
independently of the (expensive, rate-limited) generation stage below it.
"""

from dataclasses import dataclass

import feedparser
import httpx

from app.core.config import get_settings

settings = get_settings()


@dataclass
class RawArticle:
    title: str
    url: str
    summary: str
    source: str
    published_at: str


def fetch_recent_articles(max_per_feed: int = 8) -> list[RawArticle]:
    articles: list[RawArticle] = []
    with httpx.Client(timeout=10.0, headers={"User-Agent": "AIAcademyDailyPulse/1.0"}) as client:
        for feed_url in settings.daily_pulse_rss_feeds:
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
            except httpx.HTTPError:
                # One dead feed shouldn't take down the whole ingestion run
                # -- the agent works with whatever feeds actually respond.
                continue

            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:max_per_feed]:
                articles.append(
                    RawArticle(
                        title=getattr(entry, "title", "").strip(),
                        url=getattr(entry, "link", ""),
                        summary=getattr(entry, "summary", "")[:500],
                        source=parsed.feed.get("title", feed_url),
                        published_at=getattr(entry, "published", ""),
                    )
                )
    return articles
