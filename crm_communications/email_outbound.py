from __future__ import annotations

from email.utils import make_msgid
from pathlib import Path
import re

from django.conf import settings
from django.core.files.base import File
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.utils import timezone

from crm_communications.email_inbound import EMAIL_MESSAGE_ID_ROUTE_TYPE, EMAIL_THREAD_ROUTE_TYPE
from crm_communications.models import (
    CommunicationChannelCode,
    ConversationRoute,
    ErrorClass,
    Message,
    MessageAttachment,
    MessageDirection,
    MessageStatus,
)
from crm_communications.services import CommunicationTouchService, MessageQueueService, build_message_preview, normalize_email


def _clean_message_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    return normalized.strip().lower()


def _is_safe_message_id(value: str) -> bool:
    normalized = _clean_message_id(value)
    if not normalized:
        return False
    if len(normalized) > 255:
        return False
    return re.fullmatch(r"[^\s<>]+", normalized) is not None


def _sanitize_message_id(value: str) -> str:
    normalized = _clean_message_id(value)
    return normalized if _is_safe_message_id(normalized) else ""


class EmailOutboundMessageService:
    @staticmethod
    def _normalize_recipient_key(value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        if normalized.startswith("email:"):
            normalized = normalized.removeprefix("email:")
        normalized = normalize_email(normalized)
        if normalized and "@" in normalized:
            return normalized
        return ""

    @staticmethod
    def _resolve_recipient_email(*, message: Message) -> str:
        explicit_recipient = str(message.external_recipient_key or "").strip()
        if explicit_recipient:
            normalized = EmailOutboundMessageService._normalize_recipient_key(explicit_recipient)
            if normalized:
                return normalized

        candidates = [
            normalize_email(getattr(getattr(message, "contact", None), "email", "")),
            normalize_email(getattr(getattr(message, "deal", None), "lead", None) and getattr(message.deal.lead, "email", "")),
            normalize_email(getattr(getattr(message, "client", None), "email", "")),
        ]
        for candidate in candidates:
            if candidate:
                return candidate

        latest_incoming = (
            Message.objects.filter(
                conversation=message.conversation,
                channel=CommunicationChannelCode.EMAIL,
                direction=MessageDirection.INCOMING,
            )
            .exclude(external_sender_key="")
            .order_by("-received_at", "-created_at", "-id")
            .first()
        )
        fallback_sender = EmailOutboundMessageService._normalize_recipient_key(
            getattr(latest_incoming, "external_sender_key", "")
        )
        if fallback_sender:
            return fallback_sender
        return ""

    @staticmethod
    def _resolve_thread_key(*, message: Message) -> str:
        route = (
            ConversationRoute.objects.filter(
                conversation=message.conversation,
                channel=CommunicationChannelCode.EMAIL,
                route_type=EMAIL_THREAD_ROUTE_TYPE,
            )
            .order_by("-is_primary", "-id")
            .first()
        )
        return _sanitize_message_id(getattr(route, "route_key", ""))

    @staticmethod
    def _resolve_latest_message_id(*, message: Message) -> str:
        latest_thread_message = (
            Message.objects.filter(
                conversation=message.conversation,
                channel=CommunicationChannelCode.EMAIL,
            )
            .exclude(pk=message.pk)
            .exclude(external_message_id="")
            .order_by("-received_at", "-sent_at", "-created_at", "-id")
            .first()
        )
        return _sanitize_message_id(getattr(latest_thread_message, "external_message_id", ""))

    @staticmethod
    def _ensure_outbound_message_id(*, message: Message) -> str:
        existing = _sanitize_message_id(message.external_message_id)
        if existing:
            return existing
        domain = ""
        default_from_email = str(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
        if "@" in default_from_email:
            domain = default_from_email.split("@", 1)[1].strip()
        generated = _clean_message_id(make_msgid(domain=domain))
        message.external_message_id = generated
        message.save(update_fields=["external_message_id", "updated_at"])
        return generated

    @staticmethod
    def _build_thread_headers(*, message: Message, current_message_id: str) -> tuple[str, str]:
        thread_key = EmailOutboundMessageService._resolve_thread_key(message=message)
        latest_message_id = _sanitize_message_id(message.in_reply_to) or EmailOutboundMessageService._resolve_latest_message_id(message=message)
        in_reply_to = latest_message_id

        references_parts: list[str] = []
        if thread_key:
            references_parts.append(thread_key)
        if latest_message_id and latest_message_id not in references_parts:
            references_parts.append(latest_message_id)
        references = " ".join(part for part in references_parts if part and part != current_message_id)
        return in_reply_to, references

    @staticmethod
    def _attach_message_files(*, email_message: EmailMultiAlternatives, message: Message) -> None:
        for attachment in message.attachments.all().order_by("id"):
            if not attachment.file:
                continue
            attachment.file.open("rb")
            try:
                payload = attachment.file.read()
            finally:
                attachment.file.close()
            email_message.attach(
                attachment.original_name or Path(attachment.file.name).name,
                payload,
                attachment.mime_type or "application/octet-stream",
            )

    @staticmethod
    def send_message(*, message: Message) -> Message:
        if message.channel != CommunicationChannelCode.EMAIL:
            raise ValueError("EmailOutboundMessageService работает только с email-сообщениями.")
        if message.direction != MessageDirection.OUTGOING:
            raise ValueError("Отправлять можно только исходящее сообщение.")

        recipient = EmailOutboundMessageService._resolve_recipient_email(message=message)
        queued_message = Message.objects.get(pk=message.pk)
        if queued_message.status != MessageStatus.QUEUED:
            MessageQueueService.enqueue_message(message=queued_message, force=True)
            queued_message.refresh_from_db()
        attempt = MessageQueueService.begin_send_attempt(message=queued_message)

        if not recipient:
            return MessageQueueService.mark_attempt_failed(
                message=queued_message,
                attempt=attempt,
                error_class=ErrorClass.MANUAL_REQUIRED,
                error_code="missing_email_recipient",
                error_message="Не найден email получателя.",
                provider_response_payload={},
            )

        current_message_id = EmailOutboundMessageService._ensure_outbound_message_id(message=queued_message)
        in_reply_to, references = EmailOutboundMessageService._build_thread_headers(
            message=queued_message,
            current_message_id=current_message_id,
        )
        headers = {"Message-ID": f"<{current_message_id}>"}
        if in_reply_to:
            headers["In-Reply-To"] = f"<{in_reply_to}>"
        if references:
            headers["References"] = " ".join(f"<{item}>" for item in references.split())

        subject = str(queued_message.subject or "").strip() or "Сообщение"
        body_text = str(queued_message.body_text or "").strip()
        from_email = str(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "no-reply@localhost").strip()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=from_email,
            to=[recipient],
            headers=headers,
        )
        if queued_message.body_html:
            email_message.attach_alternative(queued_message.body_html, "text/html")
        EmailOutboundMessageService._attach_message_files(email_message=email_message, message=queued_message)

        try:
            sent_count = email_message.send(fail_silently=False)
        except Exception as exc:
            return MessageQueueService.mark_attempt_failed(
                message=queued_message,
                attempt=attempt,
                error_class=ErrorClass.TEMPORARY,
                error_code="smtp_send_failed",
                error_message=f"{type(exc).__name__}: {exc}",
                provider_response_payload={},
            )

        if not sent_count:
            return MessageQueueService.mark_attempt_failed(
                message=queued_message,
                attempt=attempt,
                error_class=ErrorClass.TEMPORARY,
                error_code="smtp_send_failed",
                error_message="SMTP backend не подтвердил отправку.",
                provider_response_payload={"sent_count": sent_count},
            )

        sent_message = MessageQueueService.mark_attempt_succeeded(
            message=queued_message,
            attempt=attempt,
            provider_message_id=current_message_id,
            provider_response_payload={"sent_count": sent_count},
        )
        CommunicationTouchService.ensure_touch_for_message(
            message=sent_message,
            happened_at=sent_message.sent_at or timezone.now(),
        )
        sent_message.external_recipient_key = f"email:{recipient}"
        sent_message.in_reply_to = _sanitize_message_id(in_reply_to)
        sent_message.references = " ".join(_sanitize_message_id(item) for item in references.split() if _sanitize_message_id(item))
        sent_message.save(update_fields=["external_recipient_key", "in_reply_to", "references", "updated_at"])

        thread_key = EmailOutboundMessageService._resolve_thread_key(message=sent_message) or current_message_id
        if not EmailOutboundMessageService._resolve_thread_key(message=sent_message):
            ConversationRoute.objects.update_or_create(
                channel=CommunicationChannelCode.EMAIL,
                route_type=EMAIL_THREAD_ROUTE_TYPE,
                route_key=thread_key,
                defaults={
                    "conversation": sent_message.conversation,
                    "client": sent_message.client,
                    "contact": sent_message.contact,
                    "deal": sent_message.deal,
                    "is_primary": True,
                    "resolution_source": "smtp_outbound",
                },
            )
        ConversationRoute.objects.update_or_create(
            channel=CommunicationChannelCode.EMAIL,
            route_type=EMAIL_MESSAGE_ID_ROUTE_TYPE,
            route_key=current_message_id,
            defaults={
                "conversation": sent_message.conversation,
                "client": sent_message.client,
                "contact": sent_message.contact,
                "deal": sent_message.deal,
                "is_primary": False,
                "resolution_source": "smtp_outbound",
            },
        )

        conversation = sent_message.conversation
        conversation.last_message = sent_message
        conversation.last_message_direction = MessageDirection.OUTGOING
        conversation.last_message_preview = build_message_preview(sent_message.body_text or sent_message.subject or "Email")
        conversation.last_message_at = sent_message.sent_at or timezone.now()
        conversation.last_outgoing_at = sent_message.sent_at or timezone.now()
        conversation.save(
            update_fields=[
                "last_message",
                "last_message_direction",
                "last_message_preview",
                "last_message_at",
                "last_outgoing_at",
                "updated_at",
            ]
        )
        return sent_message

    @staticmethod
    def send_due_messages(*, limit: int = 50) -> dict:
        now = timezone.now()
        queryset = (
            Message.objects.filter(
                channel=CommunicationChannelCode.EMAIL,
                direction=MessageDirection.OUTGOING,
                status=MessageStatus.QUEUED,
            )
            .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
            .order_by("queued_at", "id")[:limit]
        )
        sent_count = 0
        failed_count = 0
        manual_retry_count = 0
        processed_ids = []
        for message in queryset:
            processed_message = EmailOutboundMessageService.send_message(message=message)
            processed_ids.append(processed_message.pk)
            if processed_message.status == MessageStatus.SENT:
                sent_count += 1
            elif processed_message.status == MessageStatus.REQUIRES_MANUAL_RETRY:
                manual_retry_count += 1
            else:
                failed_count += 1
        return {
            "processed": len(processed_ids),
            "sent": sent_count,
            "failed": failed_count,
            "manual_retry": manual_retry_count,
            "message_ids": processed_ids,
        }
