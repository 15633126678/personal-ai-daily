from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .collect import collect
from .config import load_all
from .llm import enrich
from .mail import send
from .models import Article
from .rank import cluster, score
from .render import build_site, daily_markdown, save_event_data, weekly_markdown


def run_daily(root: Path, target: date, fixture: Path | None = None, send_email: bool = True) -> Path:
    profile, settings, sources, feedback = load_all(root)
    if fixture:
        raw = json.loads(fixture.read_text(encoding="utf-8"))
        articles = [Article.model_validate(a) for a in raw]
        failures: list[str] = []
    else:
        articles, failures = collect(sources, target, settings.tz)
    events = score(cluster(articles), profile, feedback)
    events = [e for e in events if e.total_score >= settings.minimum_score][:settings.max_items]
    events = enrich(events, profile, settings)
    report = daily_markdown(target, events, failures, settings)
    destination = root / "reports" / "daily" / f"{target.isoformat()}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    save_event_data(root / "data" / "events" / f"{target.isoformat()}.json", events, failures)
    build_site(root, settings)
    sent_marker = root / "data" / "sent" / f"{target.isoformat()}.daily"
    if send_email and not sent_marker.exists():
        send(f"{settings.email.subject_prefix} · {target.isoformat()}", report, settings.email)
        if settings.email.enabled:
            sent_marker.parent.mkdir(parents=True, exist_ok=True)
            sent_marker.write_text(datetime.now(settings.tz).isoformat(), encoding="utf-8")
    return destination


def run_weekly(root: Path, target: date, send_email: bool = True) -> Path:
    _, settings, _, _ = load_all(root)
    start = target - timedelta(days=6)
    files = [root / "reports" / "daily" / f"{(start + timedelta(days=i)).isoformat()}.md" for i in range(7)]
    files = [p for p in files if p.exists()]
    if not files:
        raise RuntimeError("过去七天没有日报，无法生成周报")
    iso = target.isocalendar()
    label = f"{iso.year}-W{iso.week:02d}"
    report = weekly_markdown(label, files, settings)
    destination = root / "reports" / "weekly" / f"{label}.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    build_site(root, settings)
    marker = root / "data" / "sent" / f"{label}.weekly"
    if send_email and not marker.exists():
        send(f"{settings.email.subject_prefix}周报 · {label}", report, settings.email)
        if settings.email.enabled:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(datetime.now(settings.tz).isoformat(), encoding="utf-8")
    return destination

