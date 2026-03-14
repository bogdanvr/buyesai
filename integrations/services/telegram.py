import logging
import math
from html import escape

import requests
from django.conf import settings
from django.utils import timezone
from requests import RequestException


logger = logging.getLogger(__name__)


def handle_telegram_event(payload: dict) -> dict:
    logger.info("Telegram event received: %s", payload.get("update_id"))
    return {"ok": True, "provider": "telegram"}


def send_telegram_chat_message(*, chat_id: str, text: str) -> dict:
    telegram_token = getattr(settings, "BOT_TOKEN", "")
    normalized_chat_id = str(chat_id or "").strip()
    if not telegram_token or not normalized_chat_id:
        return {"ok": False, "error": "telegram_not_configured"}

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    params = {
        "chat_id": normalized_chat_id,
        "text": str(text or "").strip(),
        "parse_mode": "HTML",
    }
    try:
        response = requests.post(url, params=params, timeout=10)
        if response.ok:
            return {"ok": True}
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("description") or payload)
        except ValueError:
            detail = response.text
        detail = (detail or "").replace("\n", " ").strip()[:300]
        logger.warning(
            "Telegram direct send failed. chat_id=%s status=%s detail=%s",
            normalized_chat_id,
            response.status_code,
            detail,
        )
        return {"ok": False, "error": detail or f"http_{response.status_code}"}
    except RequestException as exc:
        logger.exception("Telegram direct send exception. chat_id=%s", normalized_chat_id)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def format_deadline_minutes(minutes_left: int) -> str:
    total_minutes = max(1, int(minutes_left))
    if total_minutes < 60:
        return f"{total_minutes} мин"

    hours, minutes = divmod(total_minutes, 60)
    if hours < 24:
        if minutes:
            return f"{hours} ч {minutes} мин"
        return f"{hours} ч"

    days, rem_hours = divmod(hours, 24)
    chunks = [f"{days} д"]
    if rem_hours:
        chunks.append(f"{rem_hours} ч")
    if minutes:
        chunks.append(f"{minutes} мин")
    return " ".join(chunks)


def build_task_deadline_reminder_message(*, task, minutes_left: int | None = None) -> str:
    if minutes_left is None:
        if task.due_at is None:
            minutes_left = 30
        else:
            delta_seconds = max(0, (task.due_at - timezone.now()).total_seconds())
            minutes_left = max(1, math.ceil(delta_seconds / 60))

    lines = ["<b>Напоминание о дедлайне задачи</b>", f"<b>Тема:</b> {escape(task.subject)}"]
    if task.description:
        lines.append(f"<b>Описание:</b> {escape(task.description)}")
    if task.due_at:
        lines.append(f"<b>Срок:</b> {escape(task.due_at.strftime('%d.%m.%Y %H:%M'))}")
    lines.append(f"<b>До дедлайна:</b> {escape(format_deadline_minutes(minutes_left))}")
    if task.deal_id and task.deal:
        lines.append(f"<b>Сделка:</b> {escape(task.deal.title)}")
    if task.client_id and task.client:
        lines.append(f"<b>Компания:</b> {escape(task.client.name)}")
    lines.append("<b>Статус:</b> Открыта")
    return "\n".join(lines)
