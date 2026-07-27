from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

from .config import Profile
from .models import Article, Event, Feedback


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[\w\u4e00-\u9fff]{2,}", text.lower()))


def similar(a: Article, b: Article) -> bool:
    ta, tb = tokens(a.title), tokens(b.title)
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    sequence = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
    return jaccard >= 0.42 or sequence >= 0.72


def cluster(articles: list[Article]) -> list[Event]:
    groups: list[list[Article]] = []
    for article in sorted(articles, key=lambda x: x.published_at):
        group = next((g for g in groups if any(similar(article, other) for other in g)), None)
        if group is None:
            groups.append([article])
        else:
            group.append(article)
    events: list[Event] = []
    for group in groups:
        primary = max(group, key=lambda x: (x.trust, len(x.summary)))
        event_id = hashlib.sha256("|".join(sorted(a.id for a in group)).encode()).hexdigest()[:12]
        events.append(Event(
            id=event_id, title=primary.title, summary=primary.summary or primary.title,
            category=primary.category, articles=group, source_count=len({a.source for a in group}),
        ))
    return events


def _matches(text: str, values: list[str]) -> list[str]:
    lowered = text.lower()
    return [value for value in values if value.lower() in lowered]


def score(events: list[Event], profile: Profile, feedback: list[Feedback]) -> list[Event]:
    feedback_bias: dict[str, float] = {}
    for item in feedback:
        feedback_bias[item.event_id] = feedback_bias.get(item.event_id, 0) + (0.5 if item.value == "important" else -0.5)
    for event in events:
        text = f"{event.title} {event.summary}"
        entity_hits = _matches(text, profile.entities)
        region_hits = _matches(text, profile.regions)
        risk_hits = _matches(text, profile.risk_preferences)
        interest = sum(weight for topic, weight in profile.interests.items() if topic.lower() in text.lower())
        excluded = bool(_matches(text, profile.excluded_topics))
        event.credibility = min(5, max(a.trust for a in event.articles) * 3 + min(2, event.source_count - 1))
        event.importance = 1.5 + min(2, event.source_count * 0.5) + (0.5 if event.category in {"国际", "国内"} else 0)
        event.novelty = 1.0
        event.personal_relevance = interest + len(entity_hits) * 1.2 + len(region_hits) * 0.5 + len(risk_hits)
        event.personal_reason = "；".join(filter(None, [
            f"涉及关注实体：{', '.join(entity_hits)}" if entity_hits else "",
            f"匹配关注地区：{', '.join(region_hits)}" if region_hits else "",
            f"匹配你的主题或风险偏好" if interest or risk_hits else "",
        ])) or "与当前画像没有直接匹配，因公共影响入选"
        penalty = 3 if excluded else 0
        discovery_penalty = 1.5 if all(a.discovery_only for a in event.articles) else 0
        event.total_score = round(event.importance + event.credibility + event.novelty + event.personal_relevance + feedback_bias.get(event.id, 0) - penalty - discovery_penalty, 2)
    return sorted(events, key=lambda x: x.total_score, reverse=True)
