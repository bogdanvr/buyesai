from __future__ import annotations

import imaplib
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from crm_communications.models import (
    CommunicationChannelCode,
    Conversation,
    ConversationRoute,
    Message,
    MessageAttachment,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from crm_communications.services import (
    CommunicationTouchService,
    ConversationBindingService,
    ConversationResolverService,
    InboundLeadService,
    MessageQueueService,
    build_message_preview,
    normalize_email,
)


EMAIL_THREAD_ROUTE_TYPE = "email_thread"
EMAIL_MESSAGE_ID_ROUTE_TYPE = "email_message_id"


@dataclass
class ParsedInboundEmail:
    message_id: str
    thread_key: str
    subject: str
    body_text: str
    body_html: str
    from_email: str
    from_name: str
    to_email: str
    in_reply_to: str
    references: str
    received_at: datetime
    attachments: list[dict]


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return str(value or "").strip()


def _normalize_message_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    return normalized.strip().lower()


def _extract_addresses(header_value: str) -> list[tuple[str, str]]:
    return [
        (_decode_header_value(name), normalize_email(email))
        for name, email in getaddresses([header_value or ""])
        if normalize_email(email)
    ]


def _extract_text_content(email_message: EmailMessage) -> tuple[str, str, list[dict]]:
    text_chunks: list[str] = []
    html_chunks: list[str] = []
    attachments: list[dict] = []

    if email_message.is_multipart():
        for part in email_message.walk():
            content_disposition = (part.get_content_disposition() or "").lower()
            filename = _decode_header_value(part.get_filename() or "")
            if content_disposition == "attachment" or filename:
                payload = part.get_payload(decode=True) or b""
                attachments.append(
                    {
                        "filename": filename or "attachment",
                        "content": payload,
                        "mime_type": part.get_content_type() or "application/octet-stream",
                        "content_id": str(part.get("Content-ID") or "").strip(),
                        "is_inline": content_disposition == "inline",
                    }
                )
                continue
            if part.get_content_maintype() != "text":
                continue
            content = part.get_content()
            if part.get_content_type() == "text/plain":
                text_chunks.append(str(content or "").strip())
            elif part.get_content_type() == "text/html":
                html_chunks.append(str(content or "").strip())
    else:
        content = email_message.get_content()
        if email_message.get_content_type() == "text/html":
            html_chunks.append(str(content or "").strip())
        else:
            text_chunks.append(str(content or "").strip())

    body_text = "\n\n".join(chunk for chunk in text_chunks if chunk).strip()
    body_html = "\n\n".join(chunk for chunk in html_chunks if chunk).strip()
    return body_text, body_html, attachments


def _derive_body_text_from_html(body_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(body_html or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_inbound_email(raw_message: bytes) -> ParsedInboundEmail:
    email_message = BytesParser(policy=policy.default).parsebytes(raw_message)
    message_id = _normalize_message_id(email_message.get("Message-ID"))
    if not message_id:
        raise ValueError("missing_message_id")

    references_header = " ".join(_normalize_message_id(item) for item in str(email_message.get("References") or "").split() if item)
    in_reply_to = _normalize_message_id(email_message.get("In-Reply-To"))
    reference_candidates = [item for item in references_header.split() if item]
    thread_key = reference_candidates[0] if reference_candidates else (in_reply_to or message_id)

    from_addresses = _extract_addresses(email_message.get("From", ""))
    to_addresses = _extract_addresses(email_message.get("To", ""))
    from_name, from_email = from_addresses[0] if from_addresses else ("", "")
    _, to_email = to_addresses[0] if to_addresses else ("", "")

    subject = _decode_header_value(email_message.get("Subject", ""))
    body_text, body_html, attachments = _extract_text_content(email_message)
    if not body_text and body_html:
        body_text = _derive_body_text_from_html(body_html)

    date_header = email_message.get("Date")
    try:
        received_at = parsedate_to_datetime(date_header) if date_header else None
    except (TypeError, ValueError, IndexError):
        received_at = None
    if received_at is None:
        received_at = timezone.now()
    elif timezone.is_naive(received_at):
        received_at = timezone.make_aware(received_at, timezone.get_current_timezone())
    else:
        received_at = received_at.astimezone(timezone.get_current_timezone())

    return ParsedInboundEmail(
        message_id=message_id,
        thread_key=thread_key,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        in_reply_to=in_reply_to,
        references=references_header,
        received_at=received_at,
        attachments=attachments,
    )


def _message_reference_ids(parsed: ParsedInboundEmail) -> list[str]:
    references = [item for item in str(parsed.references or "").split() if item]
    ordered = []
    for candidate in [parsed.in_reply_to, *references, parsed.thread_key]:
        normalized = _normalize_message_id(candidate)
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


def _looks_like_bounce_email(parsed: ParsedInboundEmail) -> bool:
    sender = str(parsed.from_email or "").strip().lower()
    sender_local = sender.split("@", 1)[0] if sender else ""
    subject = str(parsed.subject or "").strip().lower()
    body_text = str(parsed.body_text or parsed.body_html or "").strip().lower()
    if sender_local in {"mailer-daemon", "postmaster", "maildelivery", "mail-delivery"}:
        return True
    bounce_markers = (
        "delivery status notification",
        "mail delivery failed",
        "undelivered mail",
        "returned mail",
        "delivery has failed",
        "delivery failure",
    )
    body_markers = (
        "could not be delivered",
        "this is a permanent error",
        "the following address(es) failed",
        "message was not accepted",
        "invalid mailbox",
        "user is terminated",
        "mailbox is unavailable",
    )
    return any(marker in subject for marker in bounce_markers) or any(marker in body_text for marker in body_markers)


def _extract_bounce_error_text(parsed: ParsedInboundEmail) -> str:
    lines = [str(line or "").strip() for line in str(parsed.body_text or "").splitlines()]
    interesting = []
    for line in lines:
        normalized = line.lower()
        if not normalized:
            continue
        if (
            "address(es) failed" in normalized
            or "smtp error" in normalized
            or "invalid mailbox" in normalized
            or "mailbox" in normalized
            or "user is terminated" in normalized
            or normalized.startswith("550 ")
            or "could not be delivered" in normalized
        ):
            interesting.append(line)
    if interesting:
        return "\n".join(interesting[:6])
    compact_lines = [line for line in lines if line][:6]
    return "\n".join(compact_lines)[:1000]


def _resolve_bounced_outgoing_message(parsed: ParsedInboundEmail) -> Message | None:
    reference_ids = _message_reference_ids(parsed)
    if not reference_ids:
        return None
    return (
        Message.objects.select_related("conversation", "client", "contact", "deal")
        .filter(
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            external_message_id__in=reference_ids,
        )
        .order_by("-sent_at", "-created_at", "-id")
        .first()
    )


class EmailInboundService:
    @staticmethod
    @transaction.atomic
    def process_raw_email(*, raw_message: bytes) -> dict:
        parsed = parse_inbound_email(raw_message)
        existing = Message.objects.filter(
            channel=CommunicationChannelCode.EMAIL,
            external_message_id=parsed.message_id,
        ).first()
        if existing is not None:
            return {
                "ok": True,
                "provider": "email",
                "duplicate": True,
                "message_id": existing.pk,
                "conversation_id": existing.conversation_id,
                "external_message_id": parsed.message_id,
            }

        bounced_message = _resolve_bounced_outgoing_message(parsed) if _looks_like_bounce_email(parsed) else None

        if bounced_message is not None:
            resolution = ConversationResolverService.resolve_for_email(
                email=parsed.from_email,
                route_type=EMAIL_THREAD_ROUTE_TYPE,
                route_key=parsed.thread_key,
            )
            resolution.client = bounced_message.client
            resolution.contact = bounced_message.contact
            resolution.deal = bounced_message.deal
            resolution.lead = getattr(getattr(bounced_message, "touch", None), "lead", None) or getattr(getattr(bounced_message, "deal", None), "lead", None)
            conversation = bounced_message.conversation
        else:
            resolution = ConversationResolverService.resolve_for_email(
                email=parsed.from_email,
                route_type=EMAIL_THREAD_ROUTE_TYPE,
                route_key=parsed.thread_key,
            )
            conversation = getattr(getattr(resolution, "matched_route", None), "conversation", None)
        if resolution.deal is None and resolution.lead is None and not resolution.requires_manual_binding:
            resolution.lead = InboundLeadService.create_email_lead(
                from_email=parsed.from_email,
                from_name=parsed.from_name,
                subject=parsed.subject,
                body_text=parsed.body_text,
                client=resolution.client,
            )
            resolution.client = resolution.lead.client
            resolution.resolution_notes.append("created_new_lead")
        if conversation is None:
            conversation = Conversation.objects.create(
                channel=CommunicationChannelCode.EMAIL,
                client=resolution.client,
                contact=resolution.contact,
                deal=resolution.deal,
                subject=parsed.subject or parsed.from_name or parsed.from_email or f"Email thread {parsed.thread_key}",
                status="active",
                requires_manual_binding=resolution.requires_manual_binding,
            )
            ConversationBindingService.bind_conversation(
                conversation=conversation,
                channel=CommunicationChannelCode.EMAIL,
                route_type=EMAIL_THREAD_ROUTE_TYPE,
                route_key=parsed.thread_key,
                client=resolution.client,
                contact=resolution.contact,
                deal=resolution.deal,
                resolution_source="imap_inbound",
            )
            if resolution.requires_manual_binding:
                conversation.requires_manual_binding = True
        else:
            conversation.client = resolution.client
            conversation.contact = resolution.contact
            conversation.deal = resolution.deal
            conversation.requires_manual_binding = resolution.requires_manual_binding

        message = Message.objects.create(
            conversation=conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.INCOMING,
            message_type=MessageType.EMAIL,
            status=MessageStatus.RECEIVED,
            client=resolution.client,
            contact=resolution.contact,
            deal=resolution.deal,
            external_sender_key=f"email:{parsed.from_email}" if parsed.from_email else "",
            external_recipient_key=f"email:{parsed.to_email}" if parsed.to_email else "",
            subject=parsed.subject,
            body_text=parsed.body_text,
            body_html=parsed.body_html,
            body_preview=build_message_preview(parsed.body_text or parsed.subject or parsed.from_email),
            external_message_id=parsed.message_id,
            in_reply_to=parsed.in_reply_to,
            references=parsed.references,
            provider_thread_key=parsed.thread_key,
            received_at=parsed.received_at,
        )

        ConversationRoute.objects.update_or_create(
            channel=CommunicationChannelCode.EMAIL,
            route_type=EMAIL_MESSAGE_ID_ROUTE_TYPE,
            route_key=parsed.message_id,
            defaults={
                "conversation": conversation,
                "client": resolution.client,
                "contact": resolution.contact,
                "deal": resolution.deal,
                "is_primary": False,
                "resolution_source": "imap_inbound",
            },
        )

        EmailInboundService._create_attachments(message=message, attachments=parsed.attachments)
        CommunicationTouchService.ensure_touch_for_message(
            message=message,
            happened_at=parsed.received_at,
        )
        CommunicationTouchService.ensure_lead_for_message_touch(message=message, lead=resolution.lead)
        if bounced_message is not None:
            MessageQueueService.mark_message_bounced(
                message=bounced_message,
                error_message=_extract_bounce_error_text(parsed),
                happened_at=parsed.received_at,
            )
        EmailInboundService._refresh_conversation_snapshot(conversation=conversation, message=message)
        return {
            "ok": True,
            "provider": "email",
            "duplicate": False,
            "message_id": message.pk,
            "conversation_id": conversation.pk,
            "external_message_id": parsed.message_id,
            "attachment_count": len(parsed.attachments),
        }

    @staticmethod
    def _create_attachments(*, message: Message, attachments: list[dict]) -> None:
        for item in attachments:
            filename = str(item.get("filename") or "attachment").strip() or "attachment"
            content = item.get("content") or b""
            attachment = MessageAttachment.objects.create(
                message=message,
                original_name=filename[:255],
                mime_type=str(item.get("mime_type") or "application/octet-stream").strip(),
                size_bytes=len(content),
                content_id=str(item.get("content_id") or "").strip(),
                is_inline=bool(item.get("is_inline")),
            )
            attachment.file.save(Path(filename).name, ContentFile(content), save=True)

    @staticmethod
    def _refresh_conversation_snapshot(*, conversation: Conversation, message: Message) -> None:
        conversation.last_message = message
        conversation.last_message_direction = MessageDirection.INCOMING
        conversation.last_message_preview = message.body_preview
        conversation.last_message_at = message.received_at
        conversation.last_incoming_at = message.received_at
        conversation.save(
            update_fields=[
                "client",
                "contact",
                "deal",
                "requires_manual_binding",
                "last_message",
                "last_message_direction",
                "last_message_preview",
                "last_message_at",
                "last_incoming_at",
                "updated_at",
            ]
        )


class ImapMailboxPoller:
    def __init__(self, *, host: str, port: int, username: str, password: str, use_ssl: bool = True, mailbox: str = "INBOX"):
        self.host = host
        self.port = int(port or 0)
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.mailbox = mailbox or "INBOX"

    def _connect(self):
        client_cls = imaplib.IMAP4_SSL if self.use_ssl else imaplib.IMAP4
        client = client_cls(self.host, self.port)
        client.login(self.username, self.password)
        return client

    def poll(self, *, limit: int = 50, search_criteria: str = "UNSEEN") -> dict:
        client = self._connect()
        try:
            client.select(self.mailbox)
            status, data = client.uid("search", None, search_criteria)
            if status != "OK":
                raise RuntimeError("imap_search_failed")
            uids = [item for item in (data[0].split() if data and data[0] else []) if item][:limit]
            processed = 0
            duplicates = 0
            message_ids: list[int] = []
            for uid in uids:
                fetch_status, fetch_data = client.uid("fetch", uid, "(RFC822)")
                if fetch_status != "OK":
                    continue
                raw_message = b""
                for chunk in fetch_data or []:
                    if isinstance(chunk, tuple) and len(chunk) == 2:
                        raw_message = chunk[1] or b""
                        break
                if not raw_message:
                    continue
                result = EmailInboundService.process_raw_email(raw_message=raw_message)
                if result.get("duplicate"):
                    duplicates += 1
                else:
                    processed += 1
                if result.get("message_id"):
                    message_ids.append(int(result["message_id"]))
            return {
                "processed": processed,
                "duplicates": duplicates,
                "message_ids": message_ids,
                "mailbox": self.mailbox,
            }
        finally:
            try:
                client.logout()
            except Exception:
                pass


def build_imap_poller_from_settings(*, mailbox: str | None = None) -> ImapMailboxPoller:
    return ImapMailboxPoller(
        host=str(getattr(settings, "IMAP_HOST", "") or "").strip(),
        port=int(getattr(settings, "IMAP_PORT", 993) or 993),
        username=str(getattr(settings, "IMAP_USER", "") or "").strip(),
        password=str(getattr(settings, "IMAP_PASSWORD", "") or "").strip(),
        use_ssl=bool(getattr(settings, "IMAP_USE_SSL", True)),
        mailbox=mailbox or str(getattr(settings, "IMAP_MAILBOX", "INBOX") or "INBOX"),
    )
