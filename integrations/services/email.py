import logging
from urllib.parse import quote

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives, send_mail
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


def build_lead_accept_email_token(*, lead, user) -> str:
    lead.ensure_assignment_notification_token()
    return signing.dumps(
        {
            "lead_id": lead.pk,
            "user_id": user.pk,
            "token": lead.assignment_notification_token,
        },
        salt="lead-accept-email",
    )


def build_lead_accept_url(*, lead, user) -> str:
    base_url = str(getattr(settings, "CRM_PUBLIC_BASE_URL", "") or "").rstrip("/")
    signed_token = build_lead_accept_email_token(lead=lead, user=user)
    encoded_token = quote(signed_token, safe="")
    if not base_url:
        return f"/api/v1/leads/accept/?token={encoded_token}"
    return f"{base_url}/api/v1/leads/accept/?token={encoded_token}"


def build_lead_assignment_escalation_email(*, lead, user, minutes_since_send: int) -> tuple[str, str, str]:
    escalation_minutes = int(getattr(settings, "LEAD_NOTIFICATION_ESCALATION_MINUTES", 10) or 10)
    subject = f"Новый лид без ответственного: {lead.title or lead.company or f'Лид #{lead.pk}'}"
    accept_url = build_lead_accept_url(lead=lead, user=user)
    lines = [
        f"Лид не был принят в Telegram в течение {escalation_minutes} минут.",
        "",
        f"Лид: {lead.title or lead.company or f'Лид #{lead.pk}'}",
    ]
    if lead.company:
        lines.append(f"Компания: {lead.company}")
    if lead.name:
        lines.append(f"Контакт: {lead.name}")
    if lead.phone:
        lines.append(f"Телефон: {lead.phone}")
    if lead.email:
        lines.append(f"Email: {lead.email}")
    lines.append(f"С момента отправки уведомления прошло: {minutes_since_send} мин")
    lines.append("")
    lines.append(f"Принять лид: {accept_url}")
    body = "\n".join(lines)
    html = (
        "<html><body>"
        "<p>Лид не был принят в Telegram.</p>"
        f"<p><strong>Лид:</strong> {lead.title or lead.company or f'Лид #{lead.pk}'}</p>"
        f"<p><a href=\"{accept_url}\" "
        "style=\"display:inline-block;padding:12px 18px;background:#4d87ff;color:#ffffff;text-decoration:none;border-radius:10px;font-weight:600;\">"
        "Принять"
        "</a></p>"
        "</body></html>"
    )
    return subject, body, html


def send_lead_assignment_escalation_email(*, email: str, lead, user, minutes_since_send: int) -> int:
    normalized_email = str(email or "").strip()
    if not normalized_email:
        return 0
    subject, body, html = build_lead_assignment_escalation_email(
        lead=lead,
        user=user,
        minutes_since_send=minutes_since_send,
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or "no-reply@localhost"
    message = EmailMultiAlternatives(subject, body, from_email, [normalized_email])
    message.attach_alternative(html, "text/html")
    return message.send(fail_silently=False)
