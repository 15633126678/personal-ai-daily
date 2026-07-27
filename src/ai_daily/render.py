from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

import markdown

from .config import Settings
from .models import Event


def source_links(event: Event) -> str:
    seen: set[str] = set()
    links = []
    for article in event.articles:
        if article.url not in seen:
            links.append(f"[{article.source}]({article.url})")
            seen.add(article.url)
    return " · ".join(links)


def event_md(event: Event, repository: str) -> str:
    issue_base = f"https://github.com/{repository}/issues/new"
    important = f"{issue_base}?template=feedback.yml&event_id={quote(event.id)}&value=important"
    unimportant = f"{issue_base}?template=feedback.yml&event_id={quote(event.id)}&value=not_important"
    inference = f"\n\n> **AI 推断：** {event.inference}" if event.inference else ""
    return (
        f"### {event.title}\n\n{event.summary}{inference}\n\n"
        f"**来源：** {source_links(event)}  \n"
        f"**评分：** {event.total_score:.1f} · **反馈：** [重要]({important}) / [不重要]({unimportant})\n"
    )


def daily_markdown(target: date, events: list[Event], failures: list[str], settings: Settings) -> str:
    chosen = events[:settings.max_items]
    personal = sorted(chosen, key=lambda x: x.personal_relevance, reverse=True)[:settings.personal_items]
    sections = []
    sections.append(f"# AI 日报 · {target.isoformat()}\n\n> 昨日重点，预计阅读 5–10 分钟。\n")
    sections.append("## 今日最重要\n\n" + "\n".join(event_md(e, settings.site.repository) for e in chosen[:settings.top_items]))
    sections.append("## 与你最相关\n\n" + "\n".join(
        f"### {e.title}\n\n**为什么值得关注：** {e.personal_reason}\n\n{source_links(e)}\n" for e in personal
    ))
    used = {e.id for e in chosen[:settings.top_items]}
    for category in ("国内", "国际", "科技商业", "AI"):
        items = [e for e in chosen if e.category == category and e.id not in used]
        if items:
            sections.append(f"## {category}\n\n" + "\n".join(event_md(e, settings.site.repository) for e in items))
    sections.append("## 值得继续观察\n\n" + "\n".join(f"- {e.title}" for e in chosen[:3]))
    if failures:
        sections.append(f"## 运行说明\n\n以下来源本次获取失败，系统已降级继续生成：{', '.join(failures)}。")
    sections.append(
        "## 免责声明\n\n内容由 AI 辅助整理，可能存在遗漏或错误，请以链接中的原始信息为准。"
        "事实摘要、媒体观点与标注为“AI 推断”的内容应分别理解；本文不构成医疗、法律或投资建议。"
    )
    return "\n\n".join(sections) + "\n"


def weekly_markdown(label: str, daily_files: list[Path], settings: Settings) -> str:
    blocks = [p.read_text(encoding="utf-8") for p in daily_files]
    links = "\n".join(f"- [{p.stem}](../daily/{p.name})" for p in daily_files)
    headlines: list[str] = []
    for block in blocks:
        for line in block.splitlines():
            if line.startswith("### "):
                title = line[4:].strip()
                if title not in headlines:
                    headlines.append(title)
    return (
        f"# AI 周报 · {label}\n\n## 本周主线\n\n"
        + "\n".join(f"- {title}" for title in headlines[:10])
        + "\n\n## 与你相关的影响\n\n本节基于每日相关性排序汇总；请结合原始来源判断。\n\n"
        + "## 下周观察清单\n\n"
        + "\n".join(f"- 继续观察：{title}" for title in headlines[:5])
        + f"\n\n## 本周日报\n\n{links}\n\n"
        + "> 周报仅使用过去七天已发布日报，不重新抓取新闻。\n"
    )


def save_event_data(path: Path, events: list[Event], failures: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "events": [e.model_dump(mode="json") for e in events],
        "failed_sources": failures,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def build_site(root: Path, settings: Settings) -> None:
    site = root / "site"
    site.mkdir(exist_ok=True)
    reports: list[tuple[Path, str, str]] = []
    for kind in ("daily", "weekly"):
        for source in sorted((root / "reports" / kind).glob("*.md"), reverse=True):
            relative = Path(kind) / f"{source.stem}.html"
            title = source.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            body = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["tables"])
            destination = site / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(page(title, body, "../" if kind else ""), encoding="utf-8")
            reports.append((relative, title, source.stem))
    cards = "\n".join(
        f'<a class="card" href="{html.escape(str(path).replace(chr(92), "/"))}"><small>{html.escape(stem)}</small><strong>{html.escape(title)}</strong><span>阅读报告 →</span></a>'
        for path, title, stem in reports
    ) or '<div class="empty">第一份日报生成后会出现在这里。</div>'
    body = f'<section class="hero"><span class="eyebrow">PERSONAL INTELLIGENCE BRIEF</span><h1>{html.escape(settings.site.title)}</h1><p>把世界的噪声，整理成与你有关的信号。</p></section><main class="grid">{cards}</main>'
    (site / "index.html").write_text(page(settings.site.title, body, ""), encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")


def page(title: str, body: str, prefix: str) -> str:
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>
:root{{--ink:#102a43;--muted:#627d98;--paper:#f5f1e8;--card:#fffdf7;--accent:#d34a24;--line:#d9d2c3}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.75 Georgia,"Noto Serif SC",serif}}body:before{{content:"";display:block;height:7px;background:var(--accent)}}nav{{max-width:960px;margin:auto;padding:24px}}nav a{{color:var(--ink);font-weight:700;text-decoration:none}}.hero,main,article{{max-width:960px;margin:auto;padding:48px 24px}}.hero{{padding-top:80px}}.eyebrow{{font:700 12px/1.2 Arial;letter-spacing:.2em;color:var(--accent)}}h1{{font-size:clamp(42px,8vw,86px);line-height:1.03;margin:.2em 0}}h2{{border-top:1px solid var(--line);padding-top:24px;margin-top:48px}}h3{{margin-top:36px}}a{{color:#9b351b}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}}.card{{display:flex;min-height:190px;flex-direction:column;padding:24px;background:var(--card);border:1px solid var(--line);text-decoration:none;color:var(--ink);box-shadow:0 8px 24px #102a4310}}.card strong{{font-size:24px;line-height:1.25;margin:14px 0;flex:1}}.card span,.card small{{color:var(--accent);font-family:Arial}}article{{background:var(--card);margin-bottom:60px;box-shadow:0 10px 40px #102a4312}}blockquote{{border-left:4px solid var(--accent);margin-left:0;padding-left:18px;color:var(--muted)}}@media(max-width:600px){{body{{font-size:16px}}.hero{{padding-top:42px}}article{{box-shadow:none}}}}
</style></head><body><nav><a href="{prefix}index.html">← 日报首页</a></nav>{'<article>'+body+'</article>' if '<section' not in body else body}</body></html>"""
