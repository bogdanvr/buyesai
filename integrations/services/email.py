import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def handle_email_event(payload: dict) -> dict:
    logger.info("Email event received: %s", payload.get("message_id"))
    return {"ok": True, "provider": "email"}


def build_task_deadline_escalation_email(*, task, minutes_since_send: int) -> tuple[str, str]:
    escalation_minutes = int(getattr(settings, "TASK_REMINDER_ESCALATION_MINUTES", 10) or 10)
    subject = f"Задача не подтверждена: {task.subject}"
    lines = [
        f"Напоминание по задаче не было подтверждено в Telegram в течение {escalation_minutes} минут.",
        "",
        f"Тема: {task.subject}",
    ]
    if task.description:
        lines.append(f"Описание: {task.description}")
    if task.due_at:
        lines.append(f"Срок: {timezone.localtime(task.due_at).strftime('%d.%m.%Y %H:%M')}")
    if task.deal_id and task.deal:
        lines.append(f"Сделка: {task.deal.title}")
    if task.client_id and task.client:
        lines.append(f"Компания: {task.client.name}")
    lines.append(f"С момента отправки reminder прошло: {minutes_since_send} мин")
    body = "\n".join(lines)
    return subject, body


def send_task_deadline_escalation_email(*, email: str, task, minutes_since_send: int) -> int:
    normalized_email = str(email or "").strip()
    if not normalized_email:
        return 0
    subject, body = build_task_deadline_escalation_email(task=task, minutes_since_send=minutes_since_send)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or "no-reply@localhost"
    return send_mail(subject, body, from_email, [normalized_email], fail_silently=False)
