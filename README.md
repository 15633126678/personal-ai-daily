# 个人 AI 日报助手

每天北京时间 08:00 汇总昨天的重要事件，生成公开网页和邮件；周日同时回顾过去七天。系统优先保证来源可追溯，并在网络、单个来源或模型不可用时降级运行。

> **隐私提醒：** 这是公开 Pages 方案。`config/profile.yaml`、个人相关性解释和反馈可能被任何人看到，请勿填写邮箱、住址、客户名称、内部项目或其他敏感信息。密码和 API 密钥只能放在 GitHub Secrets。

## 本地开始

需要 Python 3.12：

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
ai-daily daily --fixture tests/fixtures/articles.json --date 2026-07-26 --no-email
```

生成后打开 `site/index.html`。正式抓取昨天新闻：

```bash
ai-daily daily
```

生成周报：

```bash
ai-daily weekly --date 2026-07-26
```

## 个性化配置

- `config/profile.yaml`：修改职业、地区、兴趣权重、关注实体和排除主题。
- `config/sources.yaml`：增删 RSS，设置类别、可信度和是否只用于线索发现。
- `config/settings.yaml`：修改文章数量、模型、邮箱和 GitHub 仓库名。
- 把 `site.repository` 改为真实的 `GitHub用户名/仓库名`，网页反馈按钮才能正确创建 Issue。

可信度只是排序辅助，不代表事实已经确认。重大事件应有多个独立来源；`discovery_only: true` 的社区源会被降权。

## 模型与邮件

没有 `OPENAI_API_KEY` 时会使用规则生成降级日报。启用后，模型仅改写已入选事件，不允许添加来源中没有的数字或引语。

本地环境变量或 GitHub Secrets：

- `OPENAI_API_KEY`：OpenAI 或兼容服务密钥。
- `OPENAI_BASE_URL`：可选，兼容服务地址。
- `SMTP_PASSWORD`：邮件密码或应用专用密码。

若需邮件，把 `config/settings.yaml` 中 `email.enabled` 改为 `true`，并填写 SMTP 地址、发件人和收件人。密钥不要写入 YAML。

## 上线

1. 在 GitHub 建立公开仓库，把本项目推送到 `main`。
2. 在仓库 Settings → Pages 中选择 **GitHub Actions**。
3. 在 Settings → Secrets and variables → Actions 添加模型及邮件密钥。
4. 打开 Actions，手动运行“生成 AI 日报”完成首次验证。

定时表达式为 UTC 00:00，即北京时间 08:00。手动运行可填写日期补跑。任务写入 `reports/`、`data/events/` 和 `site/` 后自动提交；发送标记避免同一份报告重复发邮件。

## 已知边界

- RSS 的发布时间质量取决于来源，少数站点可能缺失或延迟。
- 首版语义去重采用标题相似度；中英文标题差异很大时可能无法自动合并。
- 带 `feedback` 标签的 Issue 会在生成日报前自动同步；只接受正文中格式正确的 `event_id` 和 `value`，并按 Issue 编号保证幂等。
- 周报仅基于七份日报生成，不重新抓取新闻；无日报时会明确失败。
