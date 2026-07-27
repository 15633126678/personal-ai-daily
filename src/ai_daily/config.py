from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field

from .models import Feedback, Source


class Profile(BaseModel):
    name: str = "读者"
    occupation: str = ""
    regions: list[str] = Field(default_factory=list)
    interests: dict[str, float] = Field(default_factory=dict)
    entities: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)
    risk_preferences: list[str] = Field(default_factory=list)


class ModelSettings(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    screening: str = "gpt-4.1-mini"
    synthesis: str = "gpt-4.1"


class EmailSettings(BaseModel):
    enabled: bool = False
    subject_prefix: str = "AI 日报"
    smtp_host: str = ""
    smtp_port: int = 465
    use_ssl: bool = True
    sender: str = ""
    recipient: str = ""


class SiteSettings(BaseModel):
    title: str = "我的 AI 日报"
    repository: str = "owner/repository"


class Settings(BaseModel):
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"
    daily_hour: int = 8
    weekly_day: str = "sunday"
    max_items: int = 12
    top_items: int = 5
    personal_items: int = 3
    minimum_score: float = 2.0
    models: ModelSettings = Field(default_factory=ModelSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    site: SiteSettings = Field(default_factory=SiteSettings)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_all(root: Path) -> tuple[Profile, Settings, list[Source], list[Feedback]]:
    config = root / "config"
    profile = Profile.model_validate(_yaml(config / "profile.yaml"))
    settings = Settings.model_validate(_yaml(config / "settings.yaml"))
    sources = [Source.model_validate(s) for s in _yaml(config / "sources.yaml").get("sources", [])]
    feedback_path = root / "data" / "feedback.json"
    raw_feedback = json.loads(feedback_path.read_text(encoding="utf-8")) if feedback_path.exists() else []
    return profile, settings, sources, [Feedback.model_validate(f) for f in raw_feedback]

