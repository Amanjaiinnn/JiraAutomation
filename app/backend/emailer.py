from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


def _env_flag(name: str, default: bool = False) -> bool:
    value = str(os.getenv(name, "")).strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _completed_story_lines(stories: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for index, story in enumerate(stories, start=1):
        summary = str(story.get("summary") or story.get("title") or f"Story {index}").strip()
        lines.append(f"- Story {index}: {summary}")
    return lines


def build_project_completion_email(epics: list[dict[str, Any]]) -> tuple[str, str]:
    normalized_epics = list(epics or [])
    total_epics = max(len(normalized_epics), 1)

    lines: list[str] = []
    for epic_index, epic in enumerate(normalized_epics, start=1):
        story_count = len(epic.get("stories", []) or [])
        completed_stories = [story for story in epic.get("stories", []) or [] if bool(story.get("completed"))]

        lines.extend(
            [
                f"Epic {epic_index}/{total_epics}",
                f"Number of stories generated : {story_count}",
                "List of user stories completed:",
            ]
        )
        if completed_stories:
            lines.extend(_completed_story_lines(completed_stories))
        else:
            lines.append("- None selected")
        if epic_index < total_epics:
            lines.append("")

    subject = f"Project Summary: {len(normalized_epics)} epics"
    return subject, "\n".join(lines)


def send_project_completion_email(
    epics: list[dict[str, Any]],
    notification_email: str = "",
) -> dict[str, Any]:
    recipient = str(notification_email or "").strip()
    if not recipient:
        return {"sent": False, "skipped": True, "recipient": "", "reason": "No notification email provided"}

    smtp_host = str(os.getenv("SMTP_HOST") or "").strip()
    if not smtp_host:
        return {"sent": False, "skipped": True, "recipient": recipient, "reason": "SMTP_HOST is not configured"}

    smtp_port = int(str(os.getenv("SMTP_PORT") or "587").strip())
    smtp_username = str(os.getenv("SMTP_USERNAME") or "").strip()
    smtp_password = str(os.getenv("SMTP_PASSWORD") or "").strip()
    smtp_from = str(os.getenv("SMTP_FROM_EMAIL") or smtp_username or "no-reply@localhost").strip()
    use_tls = _env_flag("SMTP_USE_TLS", default=True)

    subject, body = build_project_completion_email(epics)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_username:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    except Exception as exc:  # noqa: BLE001
        return {"sent": False, "skipped": False, "recipient": recipient, "reason": str(exc)}

    return {"sent": True, "skipped": False, "recipient": recipient, "reason": ""}
