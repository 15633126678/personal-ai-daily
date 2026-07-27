from __future__ import annotations

import shutil
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_daily.collect import canonical_url, day_window
from ai_daily.config import Profile
from ai_daily.models import Article
from ai_daily.pipeline import run_daily, run_weekly
from ai_daily.rank import cluster, score


def article(id: str, title: str, source: str = "来源") -> Article:
    return Article(
        id=id, title=title, url=f"https://example.com/{id}", summary=title,
        published_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 7, 27, tzinfo=timezone.utc), source=source,
        category="国际", language="zh", trust=.9,
    )


def test_url_and_timezone():
    assert canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2") == "https://example.com/a?b=2"
    start, end = day_window(date(2026, 7, 26), ZoneInfo("Asia/Shanghai"))
    assert start.hour == 0 and end.hour == 23


def test_duplicate_cluster_and_ranking():
    events = cluster([
        article("1", "多国宣布新的气候合作计划", "A"),
        article("2", "多国宣布全新气候合作计划", "B"),
        article("3", "明星发布新歌"),
    ])
    ranked = score(events, Profile(interests={"气候": 2}, excluded_topics=["明星"]), [])
    assert len(events) == 2
    assert ranked[0].source_count == 2
    assert "气候" in ranked[0].title


def test_offline_daily_weekly_and_site(tmp_path: Path):
    project = tmp_path / "project"
    shutil.copytree(Path(__file__).parents[1] / "config", project / "config")
    shutil.copytree(Path(__file__).parents[1] / "data", project / "data")
    fixture = Path(__file__).parent / "fixtures" / "articles.json"
    for day in range(20, 27):
        output = run_daily(project, date(2026, 7, day), fixture, send_email=False)
        assert output.exists()
    weekly = run_weekly(project, date(2026, 7, 26), send_email=False)
    assert weekly.exists()
    assert (project / "site" / "index.html").exists()
    assert "AI 日报" in (project / "site" / "index.html").read_text(encoding="utf-8")

