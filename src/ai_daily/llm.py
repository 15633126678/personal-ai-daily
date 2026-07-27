from __future__ import annotations

import json
import os

from openai import OpenAI
from pydantic import BaseModel

from .config import Profile, Settings
from .models import Event


class EnrichedEvent(BaseModel):
    event_id: str
    title_zh: str
    summary_zh: str
    personal_reason: str
    inference: str | None = None


class Enrichment(BaseModel):
    events: list[EnrichedEvent]


def enrich(events: list[Event], profile: Profile, settings: Settings) -> list[Event]:
    key = os.getenv("OPENAI_API_KEY")
    if not key or not events:
        return events
    client = OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL", settings.models.base_url))
    payload = [{
        "id": e.id, "title": e.title, "summary": e.summary,
        "sources": [{"name": a.source, "url": a.url} for a in e.articles],
    } for e in events]
    prompt = (
        "你是严谨的中文新闻编辑。只能根据输入事实改写，不得补充未经来源支持的数字或引语。"
        "为每个事件输出简洁中文标题、两句摘要、与用户画像的相关原因；推断必须明确标记，"
        "没有可靠推断则为 null。保留全部 event_id。\n"
        f"用户画像：{profile.model_dump_json()}\n事件：{json.dumps(payload, ensure_ascii=False)}"
    )
    try:
        response = client.beta.chat.completions.parse(
            model=settings.models.synthesis,
            messages=[{"role": "user", "content": prompt}],
            response_format=Enrichment,
        )
        parsed = response.choices[0].message.parsed
        if not parsed:
            return events
        by_id = {item.event_id: item for item in parsed.events}
        for event in events:
            if event.id in by_id:
                item = by_id[event.id]
                event.title = item.title_zh
                event.summary = item.summary_zh
                event.personal_reason = item.personal_reason
                event.inference = item.inference
    except Exception:
        return events
    return events

