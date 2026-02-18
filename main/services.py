from django.conf import settings
import requests


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def send_telegram(name, phone, message, subject):
    TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
    TELEGRAM_TOKEN = settings.BOT_TOKEN
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    text = f"{subject} Имя: {name} Телефон: {phone} Сообщение: {message}"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, params=params)
    print("url", url)
    print("params", params)
    print("telegram response", response.text)
