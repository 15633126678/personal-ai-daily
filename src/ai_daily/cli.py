from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import load_all
from .feedback import sync_github_feedback
from .pipeline import run_daily, run_weekly
from .render import build_site


def main() -> None:
    parser = argparse.ArgumentParser(description="个人 AI 日报助手")
    parser.add_argument("command", choices=["daily", "weekly", "site", "sync-feedback"])
    parser.add_argument("--date", help="目标日期 YYYY-MM-DD；日报默认昨天，周报默认今天")
    parser.add_argument("--fixture", type=Path, help="使用离线文章 JSON")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _, settings, _, _ = load_all(args.root)
    if args.command == "sync-feedback":
        print(f"新增反馈：{sync_github_feedback(args.root, settings.site.repository)}")
        return
    if args.command == "site":
        build_site(args.root, settings)
        return
    default = datetime.now(settings.tz).date() - (timedelta(days=1) if args.command == "daily" else timedelta())
    target = date.fromisoformat(args.date) if args.date else default
    output = run_daily(args.root, target, args.fixture, not args.no_email) if args.command == "daily" else run_weekly(args.root, target, not args.no_email)
    print(output)


if __name__ == "__main__":
    main()
