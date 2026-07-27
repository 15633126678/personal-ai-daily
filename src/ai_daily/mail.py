from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import markdown

from .config import EmailSettings


def send(subject: str, markdown_body: str, config: EmailSettings) -> None:
    if not config.enabled:
        return
    password = os.getenv("SMTP_PASSWORD")
    if not password or not config.sender or not config.recipient:
        raise RuntimeError("邮件已启用，但 SMTP_PASSWORD、sender 或 recipient 未配置")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.sender
    message["To"] = config.recipient
    message.set_content(markdown_body)
    message.add_alternative(markdown.markdown(markdown_body), subtype="html")
    smtp_cls = smtplib.SMTP_SSL if config.use_ssl else smtplib.SMTP
    with smtp_cls(config.smtp_host, config.smtp_port, timeout=30) as smtp:
        if not config.use_ssl:
            smtp.starttls()
        smtp.login(config.sender, password)
        smtp.send_message(message)

