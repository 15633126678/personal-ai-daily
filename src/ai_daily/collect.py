from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx
from bs4 import BeautifulSoup

from .models import Article, Source

log = logging.getLogger(__name__)
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in TRACKING])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(value or "", "html.parser").get_text(" ")).strip()


def parse_datetime(entry: dict) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except (TypeError, ValueError, OverflowError):
            pass
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*parsed[:6], tzinfo=timezone.utc) if parsed else None


def day_window(target: date, tz) -> tuple[datetime, datetime]:
    return datetime.combine(target, time.min, tzinfo=tz), datetime.combine(target, time.max, tzinfo=tz)


def fetch_source(client: httpx.Client, source: Source, fetched_at: datetime) -> list[Article]:
    response = client.get(str(source.url), follow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    articles: list[Article] = []
    for entry in feed.entries:
        published = parse_datetime(entry)
        url = canonical_url(entry.get("link", ""))
        title = plain_text(entry.get("title", ""))
        if not published or not url or not title:
            continue
        item_id = hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]
        articles.append(Article(
            id=item_id, title=title, url=url,
            summary=plain_text(entry.get("summary", entry.get("description", "")))[:1500],
            published_at=published, fetched_at=fetched_at, source=source.name,
            category=source.category, language=source.language, trust=source.trust,
            discovery_only=source.discovery_only,
        ))
    return articles


def collect(sources: list[Source], target: date, tz, timeout: float = 20) -> tuple[list[Article], list[str]]:
    start, end = day_window(target, tz)
    items: list[Article] = []
    failures: list[str] = []
    fetched_at = datetime.now(timezone.utc)
    with httpx.Client(timeout=timeout, headers={"User-Agent": "ai-daily-brief/0.1"}) as client:
        for source in sources:
            if not source.enabled:
                continue
            try:
                items.extend(a for a in fetch_source(client, source, fetched_at) if start <= a.published_at.astimezone(tz) <= end)
            except Exception as exc:
                log.warning("来源失败 %s: %s", source.name, exc)
                failures.append(source.name)
    unique = {canonical_url(a.url): a for a in items}
    return list(unique.values()), failures

