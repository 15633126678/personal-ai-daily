from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    name: str
    url: HttpUrl
    category: str
    language: str = "zh"
    trust: float = Field(default=0.7, ge=0, le=1)
    discovery_only: bool = False
    enabled: bool = True


class Article(BaseModel):
    id: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime
    fetched_at: datetime
    source: str
    category: str
    language: str
    trust: float
    discovery_only: bool = False


class Event(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    articles: list[Article]
    source_count: int = 1
    importance: float = 0
    credibility: float = 0
    novelty: float = 0
    personal_relevance: float = 0
    total_score: float = 0
    personal_reason: str = ""
    inference: str | None = None


class Feedback(BaseModel):
    event_id: str
    value: Literal["important", "not_important"]
    created_at: datetime
    note: str = ""

