from __future__ import annotations

import json
from pathlib import Path

import httpx

from ai_daily.feedback import sync_github_feedback


def test_feedback_sync_is_idempotent(tmp_path: Path, monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"number": 7, "body": "event_id: abcdef12\nvalue: important"}]

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response())
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "feedback.json").write_text("[]", encoding="utf-8")
    assert sync_github_feedback(tmp_path, "owner/repo") == 1
    assert sync_github_feedback(tmp_path, "owner/repo") == 0
    saved = json.loads((tmp_path / "data" / "feedback.json").read_text(encoding="utf-8"))
    assert saved[0]["event_id"] == "abcdef12"

