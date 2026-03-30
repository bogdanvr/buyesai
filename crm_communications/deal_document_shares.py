from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from crm.models import Deal, DealDocument
from crm_communications.models import (
    DealDocumentShare,
    DealDocumentShareEvent,
    DealDocumentShareEventType,
    Message,
    MessageStatus,
)


def _request_ip_address(request) -> str:
    forwarded_for = str(request.META.get("HTTP_X_FORWARDED_FOR", "") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return str(request.META.get("REMOTE_ADDR", "") or "").strip()


def _request_user_agent(request) -> str:
    return str(request.META.get("HTTP_USER_AGENT", "") or "").strip()


def build_share_public_url(*, share: DealDocumentShare, request=None) -> str:
    relative_url = reverse("deal-document-share-page", kwargs={"token": share.token})
    public_base_url = str(getattr(settings, "CRM_PUBLIC_BASE_URL", "") or "").strip()
    if public_base_url:
        return urljoin(f"{public_base_url.rstrip('/')}/", relative_url.lstrip("/"))
    if request is not None:
        return request.build_absolute_uri(relative_url)
    return relative_url


def build_share_download_url(*, share: DealDocumentShare, request=None) -> str:
    relative_url = reverse("deal-document-share-download", kwargs={"token": share.token})
    public_base_url = str(getattr(settings, "CRM_PUBLIC_BASE_URL", "") or "").strip()
    if public_base_url:
        return urljoin(f"{public_base_url.rstrip('/')}/", relative_url.lstrip("/"))
    if request is not None:
        return request.build_absolute_uri(relative_url)
    return relative_url


def _message_status_event_type(message: Message) -> str:
    if str(getattr(message, "status", "") or "").strip().lower() == MessageStatus.SENT:
        return DealDocumentShareEventType.EMAIL_SENT
    return DealDocumentShareEventType.EMAIL_FAILED


def _timeline_entry(*, deal_id: int | None, result_text: str, happened_at, event_type: str, document_name: str, share: DealDocumentShare, extra_lines: list[str] | None = None) -> str:
    timestamp = timezone.localtime(happened_at or timezone.now()).strftime("%d.%m.%Y %H:%M")
    lines = [
        timestamp,
        f"Результат: {str(result_text or '').strip()}",
        f"event_type: {event_type}",
        "priority: medium",
        "title: Документ сделки",
        f"document_name: {document_name}",
        f"document_share_token: {share.token}",
        f"document_share_url: {build_share_public_url(share=share)}",
        f"document_share_download_url: {build_share_download_url(share=share)}",
    ]
    if deal_id:
        lines.append(f"deal_id: {deal_id}")
    if extra_lines:
        lines.extend([str(line or "").strip() for line in extra_lines if str(line or "").strip()])
    return "\n".join(lines)


def _append_deal_event(*, deal: Deal | None, entry: str) -> None:
    if deal is None or not getattr(deal, "pk", None):
        return
    current_events = str(getattr(deal, "events", "") or "").strip()
    updated_events = entry if not current_events else f"{entry}\n\n{current_events}"
    Deal.objects.filter(pk=deal.pk).update(events=updated_events)


def create_document_share(*, document: DealDocument, message: Message, request=None) -> DealDocumentShare:
    recipient = str(getattr(message, "external_recipient_key", "") or "").strip()
    return DealDocumentShare.objects.create(
        document=document,
        message=message,
        channel=str(getattr(message, "channel", "") or "email").strip() or "email",
        recipient=recipient,
    )


def apply_share_link_to_message(*, message: Message, share: DealDocumentShare, document_name: str, request=None) -> Message:
    public_url = build_share_public_url(share=share, request=request)
    normalized_name = str(document_name or "документу").strip() or "документу"
    existing_body_text = str(getattr(message, "body_text", "") or "").strip()
    link_text = f"Ссылка на документ: {public_url}\nPDF доступен на странице документа."
    body_text = f"{existing_body_text}\n\n{link_text}".strip() if existing_body_text else link_text

    existing_body_html = str(getattr(message, "body_html", "") or "").strip()
    link_html = (
        f'<p><a href="{escape(public_url)}">Открыть {escape(normalized_name)}</a></p>'
        "<p>PDF доступен на странице документа.</p>"
    )
    if existing_body_html:
        body_html = f"{existing_body_html}{link_html}"
    elif existing_body_text:
        body_html = (
            "".join(
                f"<p>{escape(line)}</p>"
                for line in existing_body_text.splitlines()
                if str(line or "").strip()
            )
            + link_html
        )
    else:
        body_html = link_html

    preview_source = body_text or str(getattr(message, "subject", "") or "").strip()
    message.body_text = body_text
    message.body_html = body_html
    message.body_preview = preview_source[:500]
    message.save(update_fields=["body_text", "body_html", "body_preview", "updated_at"])
    return message


@transaction.atomic
def record_share_message_status(*, share: DealDocumentShare, message: Message) -> DealDocumentShareEvent:
    share.message = message
    share.recipient = str(getattr(message, "external_recipient_key", "") or share.recipient or "").strip()
    share.save(update_fields=["message", "recipient", "updated_at"])

    document = share.document
    deal = getattr(document, "deal", None)
    document_name = str(getattr(document, "original_name", "") or getattr(getattr(document, "file", None), "name", "") or "").strip() or f"Документ #{document.pk}"
    message_status = str(getattr(message, "status", "") or "").strip()
    event_type = _message_status_event_type(message)
    if event_type == DealDocumentShareEventType.EMAIL_SENT:
        result_text = f"Письмо со ссылкой на документ отправлено: {document_name}"
    else:
        result_text = f"Ошибка отправки письма со ссылкой на документ: {document_name}"

    event = DealDocumentShareEvent.objects.create(
        share=share,
        message=message,
        event_type=event_type,
        metadata={
            "message_status": message_status,
            "recipient": share.recipient,
            "subject": str(getattr(message, "subject", "") or "").strip(),
            "last_error_message": str(getattr(message, "last_error_message", "") or "").strip(),
        },
    )
    entry = _timeline_entry(
        deal_id=getattr(deal, "pk", None),
        result_text=result_text,
        happened_at=getattr(message, "sent_at", None) or getattr(message, "failed_at", None) or event.happened_at,
        event_type=f"document_share_{event_type}",
        document_name=document_name,
        share=share,
        extra_lines=[
            f"message_id: {message.pk}",
            f"message_status: {message_status}",
            f"recipient: {share.recipient}",
            f"last_error_message: {str(getattr(message, 'last_error_message', '') or '').strip()}",
        ],
    )
    _append_deal_event(deal=deal, entry=entry)
    return event


@transaction.atomic
def record_share_page_open(*, share: DealDocumentShare, request) -> DealDocumentShareEvent:
    happened_at = timezone.now()
    ip_address = _request_ip_address(request)
    user_agent = _request_user_agent(request)
    if not share.first_opened_at:
        share.first_opened_at = happened_at
        share.first_open_ip = ip_address or None
        share.first_open_user_agent = user_agent
    share.last_opened_at = happened_at
    share.last_open_ip = ip_address or None
    share.last_open_user_agent = user_agent
    share.open_count = int(getattr(share, "open_count", 0) or 0) + 1
    share.save(
        update_fields=[
            "first_opened_at",
            "last_opened_at",
            "open_count",
            "first_open_ip",
            "last_open_ip",
            "first_open_user_agent",
            "last_open_user_agent",
            "updated_at",
        ]
    )

    event = DealDocumentShareEvent.objects.create(
        share=share,
        message=share.message,
        event_type=DealDocumentShareEventType.PAGE_OPENED,
        happened_at=happened_at,
        ip_address=ip_address or None,
        user_agent=user_agent,
        metadata={"open_count": share.open_count},
    )
    document_name = str(getattr(share.document, "original_name", "") or getattr(getattr(share.document, "file", None), "name", "") or "").strip() or f"Документ #{share.document_id}"
    entry = _timeline_entry(
        deal_id=getattr(getattr(share.document, "deal", None), "pk", None),
        result_text=f"Открыта страница документа: {document_name}",
        happened_at=happened_at,
        event_type="document_share_page_opened",
        document_name=document_name,
        share=share,
        extra_lines=[
            f"open_count: {share.open_count}",
            f"ip_address: {ip_address}",
            f"user_agent: {user_agent}",
        ],
    )
    _append_deal_event(deal=getattr(share.document, "deal", None), entry=entry)
    return event


@transaction.atomic
def record_share_pdf_download(*, share: DealDocumentShare, request) -> DealDocumentShareEvent:
    happened_at = timezone.now()
    ip_address = _request_ip_address(request)
    user_agent = _request_user_agent(request)
    share.download_count = int(getattr(share, "download_count", 0) or 0) + 1
    share.last_downloaded_at = happened_at
    share.save(update_fields=["download_count", "last_downloaded_at", "updated_at"])

    event = DealDocumentShareEvent.objects.create(
        share=share,
        message=share.message,
        event_type=DealDocumentShareEventType.PDF_DOWNLOADED,
        happened_at=happened_at,
        ip_address=ip_address or None,
        user_agent=user_agent,
        metadata={"download_count": share.download_count},
    )
    document_name = str(getattr(share.document, "original_name", "") or getattr(getattr(share.document, "file", None), "name", "") or "").strip() or f"Документ #{share.document_id}"
    entry = _timeline_entry(
        deal_id=getattr(getattr(share.document, "deal", None), "pk", None),
        result_text=f"Скачан PDF документа: {document_name}",
        happened_at=happened_at,
        event_type="document_share_pdf_downloaded",
        document_name=document_name,
        share=share,
        extra_lines=[
            f"download_count: {share.download_count}",
            f"ip_address: {ip_address}",
            f"user_agent: {user_agent}",
        ],
    )
    _append_deal_event(deal=getattr(share.document, "deal", None), entry=entry)
    return event
