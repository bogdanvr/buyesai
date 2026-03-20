from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from crm.models import AutomationMessageDraft, AutomationOutboundMessage
from crm.models.automation import AutomationOutboundMessageStatus
from crm.models.touch import normalize_touch_channel_code
from integrations.services.telegram import send_telegram_chat_message


@dataclass
class ResolvedRecipient:
    channel_code: str
    recipient: str
    recipient_display: str
    provider: str
    status: str
    error_message: str


def _normalize_channel_code(draft: AutomationMessageDraft) -> str:
    channel_name = str(getattr(getattr(draft, "proposed_channel", None), "name", "") or "").strip()
    return normalize_touch_channel_code(channel_name)


def _resolve_email_recipient(draft: AutomationMessageDraft) -> ResolvedRecipient:
    candidates = [
        ("contact.email", str(getattr(getattr(draft, "contact", None), "email", "") or "").strip()),
        ("lead.email", str(getattr(getattr(draft, "lead", None), "email", "") or "").strip()),
        ("client.email", str(getattr(getattr(draft, "client", None), "email", "") or "").strip()),
    ]
    for label, value in candidates:
        if value:
            return ResolvedRecipient(
                channel_code="email",
                recipient=value,
                recipient_display=f"{label}: {value}",
                provider="email",
                status=AutomationOutboundMessageStatus.SENT,
                error_message="",
            )
    return ResolvedRecipient(
        channel_code="email",
        recipient="",
        recipient_display="",
        provider="email",
        status=AutomationOutboundMessageStatus.FAILED,
        error_message="Не найден email получателя.",
    )


def _resolve_manual_channel_recipient(draft: AutomationMessageDraft, channel_code: str, attr_name: str) -> ResolvedRecipient:
    raw_value = str(getattr(getattr(draft, "contact", None), attr_name, "") or "").strip()
    if raw_value:
        return ResolvedRecipient(
            channel_code=channel_code,
            recipient=raw_value,
            recipient_display=raw_value,
            provider=channel_code,
            status=AutomationOutboundMessageStatus.MANUAL_REQUIRED,
            error_message=f"Автоотправка через {channel_code} не поддерживается. Нужна ручная отправка.",
        )
    return ResolvedRecipient(
        channel_code=channel_code,
        recipient="",
        recipient_display="",
        provider=channel_code,
        status=AutomationOutboundMessageStatus.FAILED,
        error_message=f"Не найден получатель для канала {channel_code}.",
    )


def _resolve_telegram_recipient(draft: AutomationMessageDraft) -> ResolvedRecipient:
    raw_value = str(getattr(getattr(draft, "contact", None), "telegram", "") or "").strip()
    if not raw_value:
        return ResolvedRecipient(
            channel_code="telegram",
            recipient="",
            recipient_display="",
            provider="telegram",
            status=AutomationOutboundMessageStatus.FAILED,
            error_message="Не найден получатель для канала telegram.",
        )
    normalized = raw_value.replace(" ", "")
    if re.fullmatch(r"-?\d+", normalized):
        return ResolvedRecipient(
            channel_code="telegram",
            recipient=normalized,
            recipient_display=normalized,
            provider="telegram",
            status=AutomationOutboundMessageStatus.SENT,
            error_message="",
        )
    return ResolvedRecipient(
        channel_code="telegram",
        recipient=raw_value,
        recipient_display=raw_value,
        provider="telegram",
        status=AutomationOutboundMessageStatus.MANUAL_REQUIRED,
        error_message="Для auto-send в Telegram нужен chat_id. Сейчас у контакта указан username/alias.",
    )


def resolve_message_recipient(draft: AutomationMessageDraft) -> ResolvedRecipient:
    channel_code = _normalize_channel_code(draft)
    if channel_code == "email":
        return _resolve_email_recipient(draft)
    if channel_code == "telegram":
        return _resolve_telegram_recipient(draft)
    if channel_code == "whatsapp":
        return _resolve_manual_channel_recipient(draft, "whatsapp", "whatsapp")
    if not channel_code:
        return ResolvedRecipient(
            channel_code="",
            recipient="",
            recipient_display="",
            provider="",
            status=AutomationOutboundMessageStatus.FAILED,
            error_message="Не указан канал отправки.",
        )
    return ResolvedRecipient(
        channel_code=channel_code,
        recipient="",
        recipient_display="",
        provider=channel_code,
        status=AutomationOutboundMessageStatus.MANUAL_REQUIRED,
        error_message=f"Для канала {channel_code} нет автоматической доставки. Нужна ручная отправка.",
    )


def _send_email_message(*, draft: AutomationMessageDraft, recipient: str) -> tuple[bool, dict, str]:
    subject = str(draft.message_subject or draft.title or "Сообщение").strip()
    body = str(draft.message_text or "").strip()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or "no-reply@localhost"
    message = EmailMultiAlternatives(subject, body, from_email, [recipient])
    sent_count = message.send(fail_silently=False)
    success = bool(sent_count)
    payload = {"sent_count": sent_count}
    error_message = "" if success else "Почтовый backend не подтвердил отправку."
    return success, payload, error_message


def _build_telegram_message_text(draft: AutomationMessageDraft) -> str:
    subject = str(draft.message_subject or draft.title or "Сообщение").strip()
    body = str(draft.message_text or "").strip()
    chunks = [f"<b>{escape(subject)}</b>"]
    if body:
        escaped_body = escape(body).replace("\n", "\n")
        chunks.append(escaped_body)
    return "\n\n".join([chunk for chunk in chunks if chunk])


def _send_telegram_message(*, draft: AutomationMessageDraft, recipient: str) -> tuple[bool, dict, str]:
    result = send_telegram_chat_message(chat_id=recipient, text=_build_telegram_message_text(draft))
    success = bool(result.get("ok"))
    error_message = "" if success else str(result.get("error") or "Telegram API не подтвердила отправку.").strip()
    return success, result, error_message


def send_automation_message_draft(draft: AutomationMessageDraft, *, acted_by=None) -> AutomationOutboundMessage:
    recipient = resolve_message_recipient(draft)
    outbound = AutomationOutboundMessage(
        automation_rule=draft.automation_rule,
        message_draft=draft,
        source_touch=draft.source_touch,
        source_event_type=draft.source_event_type,
        title=draft.title,
        message_subject=draft.message_subject,
        message_text=draft.message_text,
        channel_code=recipient.channel_code,
        provider=recipient.provider,
        recipient=recipient.recipient,
        recipient_display=recipient.recipient_display,
        status=recipient.status,
        owner=draft.owner,
        lead=draft.lead,
        deal=draft.deal,
        client=draft.client,
        contact=draft.contact,
        acted_by=acted_by,
        acted_at=timezone.now(),
    )

    if recipient.status == AutomationOutboundMessageStatus.SENT and recipient.recipient:
        try:
            if recipient.channel_code == "email":
                success, payload, error_message = _send_email_message(draft=draft, recipient=recipient.recipient)
            elif recipient.channel_code == "telegram":
                success, payload, error_message = _send_telegram_message(draft=draft, recipient=recipient.recipient)
            else:
                success, payload, error_message = False, {}, f"Для канала {recipient.channel_code} нет отправщика."
        except Exception as exc:  # pragma: no cover - protective fallback
            outbound.status = AutomationOutboundMessageStatus.FAILED
            outbound.error_message = f"{type(exc).__name__}: {exc}"
            outbound.provider_response = {}
        else:
            outbound.provider_response = payload
            if success:
                outbound.sent_at = timezone.now()
            else:
                outbound.status = AutomationOutboundMessageStatus.FAILED
                outbound.error_message = error_message
    else:
        outbound.error_message = recipient.error_message

    outbound.save()
    return outbound
