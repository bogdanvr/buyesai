import logging
import math
from html import escape

import requests
from django.conf import settings
from django.utils import timezone
from requests import RequestException

from crm.models import Activity


logger = logging.getLogger(__name__)


def handle_telegram_event(payload: dict) -> dict:
    logger.info("Telegram event received: %s", payload.get("update_id"))
    callback_query = payload.get("callback_query") if isinstance(payload, dict) else None
    if isinstance(callback_query, dict):
        return handle_telegram_callback_query(callback_query)
    return {"ok": True, "provider": "telegram"}


def _telegram_api_request(method: str, *, params: dict) -> dict:
    telegram_token = getattr(settings, "BOT_TOKEN", "")
    if not telegram_token:
        return {"ok": False, "error": "telegram_not_configured"}

    url = f"https://api.telegram.org/bot{telegram_token}/{method}"
    try:
        response = requests.post(url, params=params, timeout=10)
        if response.ok:
            payload = response.json()
            return {"ok": True, "payload": payload}
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("description") or payload)
        except ValueError:
            detail = response.text
        detail = (detail or "").replace("\n", " ").strip()[:300]
        logger.warning(
            "Telegram API call failed. method=%s status=%s detail=%s",
            method,
            response.status_code,
            detail,
        )
        return {"ok": False, "error": detail or f"http_{response.status_code}"}
    except RequestException as exc:
        logger.exception("Telegram API request exception. method=%s", method)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def send_telegram_chat_message(*, chat_id: str, text: str, reply_markup: dict | None = None) -> dict:
    normalized_chat_id = str(chat_id or "").strip()
    if not normalized_chat_id:
        return {"ok": False, "error": "telegram_not_configured"}

    params = {
        "chat_id": normalized_chat_id,
        "text": str(text or "").strip(),
        "parse_mode": "HTML",
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    return _telegram_api_request("sendMessage", params=params)


def answer_telegram_callback_query(*, callback_query_id: str, text: str = "", show_alert: bool = False) -> dict:
    normalized_id = str(callback_query_id or "").strip()
    if not normalized_id:
        return {"ok": False, "error": "missing_callback_query_id"}
    return _telegram_api_request(
        "answerCallbackQuery",
        params={
            "callback_query_id": normalized_id,
            "text": str(text or "").strip(),
            "show_alert": show_alert,
        },
    )


def edit_telegram_message_reply_markup(*, chat_id: str, message_id: int, reply_markup: dict | None = None) -> dict:
    normalized_chat_id = str(chat_id or "").strip()
    if not normalized_chat_id or not message_id:
        return {"ok": False, "error": "missing_message_target"}
    params = {
        "chat_id": normalized_chat_id,
        "message_id": int(message_id),
    }
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    return _telegram_api_request("editMessageReplyMarkup", params=params)


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


def build_task_deadline_reminder_reply_markup(*, task: Activity) -> dict:
    token = task.ensure_deadline_ack_token()
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Принял",
                    "callback_data": f"task_ack:{task.pk}:{token}",
                }
            ]
        ]
    }


def handle_telegram_callback_query(callback_query: dict) -> dict:
    callback_query_id = str(callback_query.get("id") or "").strip()
    data = str(callback_query.get("data") or "").strip()
    if not data.startswith("task_ack:"):
        answer_telegram_callback_query(callback_query_id=callback_query_id, text="Неизвестное действие")
        return {"ok": False, "error": "unsupported_callback"}

    _, task_id_raw, token = (data.split(":", 2) + ["", ""])[:3]
    try:
        task_id = int(task_id_raw)
    except (TypeError, ValueError):
        answer_telegram_callback_query(callback_query_id=callback_query_id, text="Некорректная задача")
        return {"ok": False, "error": "invalid_task_id"}

    task = (
        Activity.objects.select_related("deal", "client")
        .filter(pk=task_id, deadline_reminder_ack_token=token)
        .first()
    )
    if task is None:
        answer_telegram_callback_query(callback_query_id=callback_query_id, text="Напоминание не найдено")
        return {"ok": False, "error": "task_not_found"}

    if task.deadline_reminder_acknowledged_at is None:
        task.deadline_reminder_acknowledged_at = timezone.now()
        task.save(update_fields=["deadline_reminder_acknowledged_at", "updated_at"])
        callback_text = "Принято"
    else:
        callback_text = "Уже подтверждено"

    answer_telegram_callback_query(callback_query_id=callback_query_id, text=callback_text)

    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "").strip()
    message_id = message.get("message_id")
    if chat_id and message_id:
        edit_telegram_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup={"inline_keyboard": []})

    return {"ok": True, "provider": "telegram", "action": "task_ack", "task_id": task.pk}
