import logging
from html import escape

import requests
from django.conf import settings
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


def build_task_notification_message(*, task, created: bool) -> str:
    title = "Новая задача" if created else "Задача обновлена"
    lines = [f"<b>{escape(title)}</b>", f"<b>Тема:</b> {escape(task.subject)}"]
    if task.description:
        lines.append(f"<b>Описание:</b> {escape(task.description)}")
    if task.due_at:
        lines.append(f"<b>Срок:</b> {escape(task.due_at.strftime('%d.%m.%Y %H:%M'))}")
    if task.deal_id and task.deal:
        lines.append(f"<b>Сделка:</b> {escape(task.deal.title)}")
    if task.client_id and task.client:
        lines.append(f"<b>Компания:</b> {escape(task.client.name)}")
    if task.is_done:
        lines.append("<b>Статус:</b> Выполнена")
    else:
        lines.append("<b>Статус:</b> Открыта")
    return "\n".join(lines)
