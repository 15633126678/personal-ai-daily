from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .models import Feedback


def sync_github_feedback(root: Path, repository: str) -> int:
    """读取带 feedback 标签的 Issue；只接受明确的 event_id/value 字段。"""
    if not repository or repository == "owner/repository":
        return 0
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-daily-brief/0.1"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(
        f"https://api.github.com/repos/{repository}/issues",
        params={"labels": "feedback", "state": "all", "per_page": 100},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    path = root / "data" / "feedback.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    known = {item.get("note", "") for item in existing}
    added = 0
    for issue in response.json():
        if "pull_request" in issue:
            continue
        body = issue.get("body") or ""
        event_match = re.search(r"event_id\s*:\s*([a-f0-9]{6,32})", body, re.I)
        value_match = re.search(r"value\s*:\s*(important|not_important)", body, re.I)
        marker = f"github_issue:#{issue['number']}"
        if not event_match or not value_match or marker in known:
            continue
        item = Feedback(
            event_id=event_match.group(1),
            value=value_match.group(1).lower(),
            created_at=datetime.now(timezone.utc),
            note=marker,
        )
        existing.append(item.model_dump(mode="json"))
        known.add(marker)
        added += 1
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return added

