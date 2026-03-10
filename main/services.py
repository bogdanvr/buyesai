from django.conf import settings
import requests
from requests import RequestException
from html import escape


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_telegram_chat_ids():
    chat_candidates = [
        getattr(settings, "TELEGRAM_CHAT_CHANNEL", ""),
        getattr(settings, "TELEGRAM_SUPER_GROUP", ""),
        getattr(settings, "TELEGRAM_CHAT_ID", ""),
    ]
    chat_ids = []
    for value in chat_candidates:
        chat_id = str(value or "").strip()
        if chat_id and chat_id not in chat_ids:
            chat_ids.append(chat_id)
    return chat_ids


def _flatten_payload(payload):
    if not isinstance(payload, dict):
        return []
    lines = []
    for key, value in payload.items():
        if value in (None, "", [], {}):
            continue
        key_label = str(key).replace("_", " ").strip().capitalize()
        value_text = escape(str(value))
        lines.append(f"<b>{escape(key_label)}:</b> {value_text}")
    return lines


def send_form_to_telegram(form_type, payload):
    telegram_token = getattr(settings, "BOT_TOKEN", "")
    chat_ids = _get_telegram_chat_ids()
    if not telegram_token or not chat_ids:
        return {"sent": 0, "total": len(chat_ids), "errors": ["telegram_not_configured"]}

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload_lines = _flatten_payload(payload)
    form_type_value = escape(str(form_type or "unknown"))
    text_lines = [f"<b>Новая заявка</b>", f"<b>Форма:</b> {form_type_value}"]
    if payload_lines:
        text_lines.extend(payload_lines)
    text = "\n".join(text_lines)

    sent = 0
    errors = []
    for chat_id in chat_ids:
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            response = requests.post(url, params=params, timeout=10)
            if response.ok:
                sent += 1
            else:
                errors.append(f"{chat_id}:{response.status_code}")
        except RequestException as exc:
            errors.append(f"{chat_id}:{exc}")

    return {"sent": sent, "total": len(chat_ids), "errors": errors}


def send_telegram(name, phone, message, subject):
    payload = {
        "subject": subject,
        "name": name,
        "phone": phone,
        "message": message,
    }
    return send_form_to_telegram("legacy", payload)
