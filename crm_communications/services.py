from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as dt_timezone
from html import escape
import re
from typing import Iterable

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.models import Client, CommunicationChannel, Contact, Deal, Lead, LeadSource, LeadStatus, Touch
from crm.models.touch import TouchDirection
from crm_communications.models import (
    AttemptStatus,
    CommunicationChannelCode,
    Conversation,
    ConversationRoute,
    DeliveryFailureQueue,
    DeliveryFailureResolutionStatus,
    ErrorClass,
    Message,
    MessageAttemptLog,
    MessageDirection,
    MessageStatus,
    MessageType,
    MessageWebhookEvent,
    ParticipantBinding,
    WebhookProcessingStatus,
)
from integrations.services.telegram import send_telegram_chat_message


RETRY_BACKOFF_MINUTES = (1, 5, 15, 60)
MAX_SEND_ATTEMPTS = 5

COMMUNICATION_CHANNEL_LABELS = {
    CommunicationChannelCode.EMAIL: "Email",
    CommunicationChannelCode.TELEGRAM: "Telegram",
}


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_telegram_key(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("telegram:"):
        return raw
    return f"telegram:{raw}"


def get_active_deals_for_client(*, client: Client | None) -> list[Deal]:
    if client is None:
        return []
    queryset = (
        Deal.objects.select_related("stage")
        .filter(client=client, closed_at__isnull=True, is_won=False)
        .filter(Q(stage__isnull=True) | Q(stage__is_final=False))
    )
    return list(queryset.distinct().order_by("-created_at", "-id"))


def get_open_leads_for_client(*, client: Client | None) -> list[Lead]:
    if client is None:
        return []
    queryset = (
        Lead.objects.select_related("status", "client")
        .filter(client=client)
        .exclude(status__code__in=("converted", "archived", "lost", "unqualified", "spam"))
        .filter(Q(status__isnull=True) | Q(status__is_final=False))
    )
    return list(queryset.distinct().order_by("-created_at", "-id"))


def get_open_leads_for_email(*, email: str) -> list[Lead]:
    normalized_email = normalize_email(email)
    if not normalized_email:
        return []
    queryset = (
        Lead.objects.select_related("status", "client")
        .filter(email__iexact=normalized_email)
        .exclude(status__code__in=("converted", "archived", "lost", "unqualified", "spam"))
        .filter(Q(status__isnull=True) | Q(status__is_final=False))
    )
    return list(queryset.distinct().order_by("-created_at", "-id"))


@dataclass
class ConversationResolution:
    client: Client | None = None
    contact: Contact | None = None
    deal: Deal | None = None
    lead: Lead | None = None
    matched_route: ConversationRoute | None = None
    requires_manual_binding: bool = False
    resolution_notes: list[str] = field(default_factory=list)


class ConversationResolverService:
    @staticmethod
    def resolve_for_email(*, email: str, route_type: str = "", route_key: str = "") -> ConversationResolution:
        normalized_email = normalize_email(email)
        return ConversationResolverService._resolve(
            channel=CommunicationChannelCode.EMAIL,
            route_type=route_type,
            route_key=route_key,
            participant_keys=[f"email:{normalized_email}"] if normalized_email else [],
            email=normalized_email,
        )

    @staticmethod
    def resolve_for_telegram(*, external_participant_key: str, route_type: str = "", route_key: str = "") -> ConversationResolution:
        normalized_key = normalize_telegram_key(external_participant_key)
        return ConversationResolverService._resolve(
            channel=CommunicationChannelCode.TELEGRAM,
            route_type=route_type,
            route_key=route_key,
            participant_keys=[normalized_key] if normalized_key else [],
        )

    @staticmethod
    def _resolve(
        *,
        channel: str,
        route_type: str = "",
        route_key: str = "",
        participant_keys: Iterable[str] = (),
        email: str = "",
    ) -> ConversationResolution:
        resolution = ConversationResolution()

        if route_type and route_key:
            matched_route = (
                ConversationRoute.objects.select_related("client", "contact", "deal")
                .filter(channel=channel, route_type=route_type, route_key=route_key)
                .order_by("-is_primary", "-id")
                .first()
            )
            if matched_route:
                resolution.client = matched_route.client
                resolution.contact = matched_route.contact
                resolution.deal = matched_route.deal
                resolution.matched_route = matched_route
                resolution.resolution_notes.append("matched_by_route")
                return resolution

        for participant_key in participant_keys:
            binding = (
                ParticipantBinding.objects.select_related("client", "contact")
                .filter(channel=channel, external_participant_key=participant_key)
                .order_by("-is_primary", "-id")
                .first()
            )
            if binding:
                resolution.client = binding.client
                resolution.contact = binding.contact
                resolution.resolution_notes.append("matched_by_participant_binding")
                break

        if resolution.contact is None and email:
            contacts = list(
                Contact.objects.select_related("client")
                .filter(email__iexact=email)
                .order_by("id")
            )
            if len(contacts) == 1:
                resolution.contact = contacts[0]
                resolution.client = contacts[0].client
                resolution.resolution_notes.append("matched_by_contact_email")

        if resolution.contact is None and channel == CommunicationChannelCode.TELEGRAM:
            telegram_values = [key.removeprefix("telegram:") for key in participant_keys if key]
            if telegram_values:
                contacts = list(
                    Contact.objects.select_related("client")
                    .filter(telegram__in=telegram_values)
                    .order_by("id")
                )
                if len(contacts) == 1:
                    resolution.contact = contacts[0]
                    resolution.client = contacts[0].client
                    resolution.resolution_notes.append("matched_by_contact_telegram")

        if resolution.client is None and email:
            clients = list(Client.objects.filter(email__iexact=email).order_by("id"))
            if len(clients) == 1:
                resolution.client = clients[0]
                resolution.resolution_notes.append("matched_by_client_email")

        if resolution.client is None and resolution.contact is not None:
            resolution.client = resolution.contact.client

        active_deals = get_active_deals_for_client(client=resolution.client)
        if resolution.deal is None:
            if len(active_deals) == 1:
                resolution.deal = active_deals[0]
                resolution.lead = active_deals[0].lead
                resolution.resolution_notes.append("matched_by_single_active_deal")
            elif len(active_deals) > 1:
                resolution.requires_manual_binding = True
                resolution.resolution_notes.append("requires_manual_binding")
                return resolution

        lead_candidates: list[Lead] = []
        if resolution.deal is None and resolution.lead is None:
            if resolution.client is not None:
                lead_candidates.extend(get_open_leads_for_client(client=resolution.client))
            if email:
                for lead in get_open_leads_for_email(email=email):
                    if all(existing.pk != lead.pk for existing in lead_candidates):
                        lead_candidates.append(lead)

            if len(lead_candidates) == 1:
                resolution.lead = lead_candidates[0]
                if resolution.client is None:
                    resolution.client = lead_candidates[0].client
                resolution.resolution_notes.append("matched_by_single_open_lead")
            elif len(lead_candidates) > 1:
                resolution.requires_manual_binding = True
                resolution.resolution_notes.append("requires_manual_binding")

        return resolution


class InboundLeadService:
    @staticmethod
    def _default_new_status() -> LeadStatus | None:
        return LeadStatus.objects.filter(code="new").order_by("id").first()

    @staticmethod
    def _source_by_code(*, code: str) -> LeadSource | None:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code:
            return None
        return LeadSource.objects.filter(code=normalized_code).order_by("id").first()

    @staticmethod
    @transaction.atomic
    def create_email_lead(
        *,
        from_email: str,
        from_name: str = "",
        subject: str = "",
        body_text: str = "",
        client: Client | None = None,
    ) -> Lead:
        title = str(subject or "").strip() or f"Email от {normalize_email(from_email) or 'нового клиента'}"
        lead = Lead.objects.create(
            title=title[:255],
            description=str(body_text or "").strip(),
            name=str(from_name or "").strip(),
            email=normalize_email(from_email),
            company=str(getattr(client, "name", "") or "").strip(),
            client=client,
            status=InboundLeadService._default_new_status(),
            source=InboundLeadService._source_by_code(code="email"),
            payload={
                "channel": CommunicationChannelCode.EMAIL,
                "inbound_auto_created": True,
                "sender_email": normalize_email(from_email),
            },
        )
        return lead

    @staticmethod
    @transaction.atomic
    def create_telegram_lead(
        *,
        sender_id: str,
        sender_name: str = "",
        body_text: str = "",
        client: Client | None = None,
    ) -> Lead:
        clean_sender_id = str(sender_id or "").strip()
        title = str(sender_name or "").strip() or f"Telegram {clean_sender_id or 'новое обращение'}"
        lead = Lead.objects.create(
            title=title[:255],
            description=str(body_text or "").strip(),
            name=str(sender_name or "").strip(),
            company=str(getattr(client, "name", "") or "").strip(),
            client=client,
            status=InboundLeadService._default_new_status(),
            source=InboundLeadService._source_by_code(code="telegram"),
            payload={
                "channel": CommunicationChannelCode.TELEGRAM,
                "inbound_auto_created": True,
                "telegram_sender_id": clean_sender_id,
            },
        )
        return lead


class ConversationBindingService:
    @staticmethod
    @transaction.atomic
    def bind_conversation(
        *,
        conversation: Conversation,
        channel: str,
        route_type: str,
        route_key: str,
        client: Client | None = None,
        contact: Contact | None = None,
        deal: Deal | None = None,
        resolved_by=None,
        resolution_source: str = "manual",
        make_primary: bool = True,
    ) -> ConversationRoute:
        if make_primary:
            ConversationRoute.objects.filter(conversation=conversation, channel=channel, is_primary=True).update(is_primary=False)

        route, created = ConversationRoute.objects.update_or_create(
            channel=channel,
            route_type=route_type,
            route_key=route_key,
            defaults={
                "conversation": conversation,
                "client": client,
                "contact": contact,
                "deal": deal,
                "is_primary": make_primary,
                "resolved_by": resolved_by,
                "resolved_at": timezone.now(),
                "resolution_source": resolution_source,
            },
        )

        conversation.client = client
        conversation.contact = contact
        conversation.deal = deal
        conversation.requires_manual_binding = False
        conversation.save(
            update_fields=[
                "client",
                "contact",
                "deal",
                "requires_manual_binding",
                "updated_at",
            ]
        )
        return route

    @staticmethod
    @transaction.atomic
    def ensure_participant_binding(
        *,
        channel: str,
        external_participant_key: str,
        client: Client | None = None,
        contact: Contact | None = None,
        external_display_name: str = "",
        is_primary: bool = True,
    ) -> ParticipantBinding:
        if is_primary:
            ParticipantBinding.objects.filter(
                channel=channel,
                external_participant_key=external_participant_key,
            ).update(is_primary=False)

        binding, _ = ParticipantBinding.objects.update_or_create(
            channel=channel,
            external_participant_key=external_participant_key,
            defaults={
                "client": client,
                "contact": contact,
                "external_display_name": external_display_name,
                "is_primary": is_primary,
            },
        )
        return binding


def get_retry_delay_minutes(*, attempt_number: int) -> int | None:
    if attempt_number <= 0:
        return None
    index = attempt_number - 1
    if index >= len(RETRY_BACKOFF_MINUTES):
        return None
    return RETRY_BACKOFF_MINUTES[index]


class MessageQueueService:
    @staticmethod
    @transaction.atomic
    def enqueue_message(*, message: Message, force: bool = False) -> Message:
        if message.direction != MessageDirection.OUTGOING:
            raise ValueError("В очередь можно ставить только исходящее сообщение.")
        if message.status not in {MessageStatus.DRAFT, MessageStatus.FAILED, MessageStatus.REQUIRES_MANUAL_RETRY} and not force:
            return message

        now = timezone.now()
        message.status = MessageStatus.QUEUED
        message.queued_at = message.queued_at or now
        message.next_attempt_at = now
        message.requires_manual_retry = False
        message.save(update_fields=["status", "queued_at", "next_attempt_at", "requires_manual_retry", "updated_at"])
        DeliveryFailureQueue.objects.filter(message=message).update(
            resolution_status=DeliveryFailureResolutionStatus.CLOSED,
            resolved_at=now,
        )
        return message

    @staticmethod
    @transaction.atomic
    def begin_send_attempt(*, message: Message) -> MessageAttemptLog:
        message = Message.objects.select_for_update().get(pk=message.pk)
        latest_attempt = message.attempt_logs.order_by("-attempt_number", "-id").first()
        if message.status == MessageStatus.SENDING and latest_attempt and latest_attempt.status == AttemptStatus.STARTED:
            return latest_attempt
        if message.status != MessageStatus.QUEUED:
            raise ValueError("Начать отправку можно только для сообщения в статусе queued.")

        attempt_number = (latest_attempt.attempt_number if latest_attempt else 0) + 1
        now = timezone.now()
        attempt = MessageAttemptLog.objects.create(
            message=message,
            attempt_number=attempt_number,
            transport=message.channel,
            started_at=now,
            status=AttemptStatus.STARTED,
        )
        message.status = MessageStatus.SENDING
        message.sending_started_at = now
        message.next_attempt_at = None
        message.save(update_fields=["status", "sending_started_at", "next_attempt_at", "updated_at"])
        return attempt

    @staticmethod
    @transaction.atomic
    def mark_attempt_succeeded(
        *,
        message: Message,
        attempt: MessageAttemptLog,
        provider_message_id: str = "",
        provider_response_payload: dict | None = None,
    ) -> Message:
        now = timezone.now()
        attempt.status = AttemptStatus.SUCCEEDED
        attempt.finished_at = now
        attempt.error_class = ""
        attempt.error_code = ""
        attempt.error_message = ""
        attempt.provider_response_payload = provider_response_payload or {}
        attempt.scheduled_retry_at = None
        attempt.is_final = True
        attempt.save(
            update_fields=[
                "status",
                "finished_at",
                "error_class",
                "error_code",
                "error_message",
                "provider_response_payload",
                "scheduled_retry_at",
                "is_final",
                "updated_at",
            ]
        )

        message.status = MessageStatus.SENT
        message.sent_at = now
        message.failed_at = None
        message.requires_manual_retry = False
        message.last_error_code = ""
        message.last_error_message = ""
        message.retry_count = max(message.retry_count, attempt.attempt_number - 1)
        if provider_message_id:
            message.provider_message_id = provider_message_id
        message.save(
            update_fields=[
                "status",
                "sent_at",
                "failed_at",
                "requires_manual_retry",
                "last_error_code",
                "last_error_message",
                "retry_count",
                "provider_message_id",
                "updated_at",
            ]
        )
        DeliveryFailureQueue.objects.filter(message=message).update(
            resolution_status=DeliveryFailureResolutionStatus.RESOLVED,
            resolved_at=now,
        )
        return message

    @staticmethod
    @transaction.atomic
    def mark_attempt_failed(
        *,
        message: Message,
        attempt: MessageAttemptLog,
        error_class: str,
        error_code: str = "",
        error_message: str = "",
        provider_response_payload: dict | None = None,
    ) -> Message:
        now = timezone.now()
        normalized_error_class = error_class or ErrorClass.PERMANENT
        provider_payload = provider_response_payload or {}
        next_retry_at = None
        is_exhausted_temporary = (
            normalized_error_class == ErrorClass.TEMPORARY and attempt.attempt_number >= MAX_SEND_ATTEMPTS
        )

        if normalized_error_class == ErrorClass.TEMPORARY and not is_exhausted_temporary:
            retry_delay_minutes = get_retry_delay_minutes(attempt_number=attempt.attempt_number)
            if retry_delay_minutes is None:
                is_exhausted_temporary = True
            else:
                next_retry_at = now + timedelta(minutes=retry_delay_minutes)

        if next_retry_at is not None:
            attempt.status = AttemptStatus.RETRY_SCHEDULED
            attempt.scheduled_retry_at = next_retry_at
            attempt.is_final = False
            message.status = MessageStatus.QUEUED
            message.next_attempt_at = next_retry_at
            message.requires_manual_retry = False
            failure_type = ""
        elif normalized_error_class in {ErrorClass.MANUAL_REQUIRED} or is_exhausted_temporary:
            attempt.status = AttemptStatus.FAILED
            attempt.scheduled_retry_at = None
            attempt.is_final = True
            message.status = MessageStatus.REQUIRES_MANUAL_RETRY
            message.next_attempt_at = None
            message.requires_manual_retry = True
            failure_type = "manual_retry_required" if normalized_error_class == ErrorClass.MANUAL_REQUIRED else "retry_exhausted"
        else:
            attempt.status = AttemptStatus.FAILED
            attempt.scheduled_retry_at = None
            attempt.is_final = True
            message.status = MessageStatus.FAILED
            message.next_attempt_at = None
            message.requires_manual_retry = False
            failure_type = normalized_error_class or "failed"

        attempt.finished_at = now
        attempt.error_class = normalized_error_class
        attempt.error_code = error_code
        attempt.error_message = error_message
        attempt.provider_response_payload = provider_payload
        attempt.save(
            update_fields=[
                "status",
                "finished_at",
                "error_class",
                "error_code",
                "error_message",
                "provider_response_payload",
                "scheduled_retry_at",
                "is_final",
                "updated_at",
            ]
        )

        message.failed_at = now
        message.last_error_code = error_code
        message.last_error_message = error_message
        message.retry_count = max(message.retry_count, attempt.attempt_number)
        message.save(
            update_fields=[
                "status",
                "next_attempt_at",
                "failed_at",
                "requires_manual_retry",
                "last_error_code",
                "last_error_message",
                "retry_count",
                "updated_at",
            ]
        )

        if failure_type:
            DeliveryFailureQueue.objects.update_or_create(
                message=message,
                defaults={
                    "failure_type": failure_type,
                    "opened_at": now,
                    "last_attempt_log": attempt,
                    "resolution_status": DeliveryFailureResolutionStatus.OPEN,
                    "resolved_at": None,
                    "resolution_comment": "",
                },
            )

        return message


def build_message_preview(value: str, *, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


class CommunicationTouchService:
    @staticmethod
    def _resolve_touch_summary(*, message: Message) -> str:
        subject = str(getattr(message, "subject", "") or "").strip()
        body_preview = build_message_preview(getattr(message, "body_text", "") or getattr(message, "body_preview", "") or "", limit=240)
        channel_label = COMMUNICATION_CHANNEL_LABELS.get(message.channel, str(message.channel or "Сообщение").capitalize())
        if subject and body_preview:
            return f"{channel_label}: {subject}. {body_preview}"
        if subject:
            return f"{channel_label}: {subject}"
        if body_preview:
            return body_preview
        return f"{channel_label} сообщение"

    @staticmethod
    def _resolve_channel(*, message: Message):
        channel_name = COMMUNICATION_CHANNEL_LABELS.get(message.channel, str(message.channel or "").strip().capitalize() or "Сообщение")
        channel, _ = CommunicationChannel.objects.get_or_create(
            name=channel_name,
            defaults={"is_active": True},
        )
        return channel

    @staticmethod
    @transaction.atomic
    def ensure_touch_for_message(*, message: Message, happened_at=None) -> Touch:
        message = Message.objects.select_related("deal", "client", "contact", "author_user").get(pk=message.pk)
        if message.touch_id:
            return message.touch

        channel = CommunicationTouchService._resolve_channel(message=message)
        happened_at_value = happened_at or message.received_at or message.sent_at or message.created_at or timezone.now()
        touch = Touch.objects.create(
            happened_at=happened_at_value,
            channel=channel,
            direction=TouchDirection.INCOMING if message.direction == MessageDirection.INCOMING else TouchDirection.OUTGOING,
            summary=CommunicationTouchService._resolve_touch_summary(message=message),
            owner=message.author_user or getattr(getattr(message, "deal", None), "owner", None),
            lead=getattr(getattr(message, "deal", None), "lead", None),
            deal=message.deal,
            client=message.client,
            contact=message.contact,
        )
        message.touch = touch
        message.save(update_fields=["touch", "updated_at"])
        return touch

    @staticmethod
    @transaction.atomic
    def ensure_lead_for_message_touch(*, message: Message, lead: Lead | None) -> Touch | None:
        if lead is None:
            return getattr(message, "touch", None)
        message = Message.objects.select_related("touch").get(pk=message.pk)
        if message.touch_id is None:
            return None
        touch = message.touch
        updates: list[str] = []
        if touch.lead_id != lead.id:
            touch.lead = lead
            updates.append("lead")
        if touch.client_id is None and lead.client_id:
            touch.client = lead.client
            updates.append("client")
        if updates:
            touch.save(update_fields=[*updates, "updated_at"])
        return touch


class TelegramInboundWebhookService:
    ROUTE_TYPE = "telegram_chat"

    @staticmethod
    @transaction.atomic
    def process_update(*, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"ok": False, "error": "invalid_payload"}

        update_id = str(payload.get("update_id") or "").strip()
        webhook_event = None
        if update_id:
            webhook_event, created = MessageWebhookEvent.objects.get_or_create(
                channel=CommunicationChannelCode.TELEGRAM,
                external_event_id=update_id,
                defaults={
                    "event_type": "telegram_update",
                    "payload": payload,
                    "processing_status": WebhookProcessingStatus.PENDING,
                },
            )
            if not created and webhook_event.processing_status == WebhookProcessingStatus.PROCESSED:
                return {"ok": True, "provider": "telegram", "duplicate": True}
            if not created:
                webhook_event.payload = payload
                webhook_event.processing_status = WebhookProcessingStatus.PENDING
                webhook_event.error_message = ""
                webhook_event.save(update_fields=["payload", "processing_status", "error_message", "updated_at"])
        else:
            webhook_event = MessageWebhookEvent.objects.create(
                channel=CommunicationChannelCode.TELEGRAM,
                event_type="telegram_update",
                payload=payload,
            )

        try:
            message_payload = None
            for key in ("message", "edited_message"):
                candidate = payload.get(key)
                if isinstance(candidate, dict):
                    message_payload = candidate
                    break

            if not isinstance(message_payload, dict):
                webhook_event.processing_status = WebhookProcessingStatus.IGNORED
                webhook_event.processed_at = timezone.now()
                webhook_event.error_message = ""
                webhook_event.save(update_fields=["processing_status", "processed_at", "error_message", "updated_at"])
                return {"ok": True, "provider": "telegram", "ignored": True}

            result = TelegramInboundWebhookService._process_message(
                payload=payload,
                message_payload=message_payload,
                webhook_event=webhook_event,
            )
            webhook_event.processing_status = WebhookProcessingStatus.PROCESSED
            webhook_event.processed_at = timezone.now()
            webhook_event.external_message_id = str(result.get("external_message_id") or "")
            webhook_event.error_message = ""
            webhook_event.save(
                update_fields=[
                    "processing_status",
                    "processed_at",
                    "external_message_id",
                    "error_message",
                    "updated_at",
                ]
            )
            return result
        except Exception as exc:
            webhook_event.processing_status = WebhookProcessingStatus.FAILED
            webhook_event.error_message = str(exc)
            webhook_event.save(update_fields=["processing_status", "error_message", "updated_at"])
            raise

    @staticmethod
    def _process_message(*, payload: dict, message_payload: dict, webhook_event: MessageWebhookEvent) -> dict:
        chat = message_payload.get("chat") or {}
        sender = message_payload.get("from") or {}
        chat_id = str(chat.get("id") or "").strip()
        sender_id = str(sender.get("id") or chat_id).strip()
        if not chat_id:
            raise ValueError("missing_chat_id")

        route_key = chat_id
        participant_key = normalize_telegram_key(sender_id)
        resolution = ConversationResolverService.resolve_for_telegram(
            external_participant_key=sender_id,
            route_type=TelegramInboundWebhookService.ROUTE_TYPE,
            route_key=route_key,
        )
        if resolution.client is None and resolution.contact is None and resolution.deal is None and resolution.lead is None:
            resolution.lead = InboundLeadService.create_telegram_lead(
                sender_id=sender_id,
                sender_name=TelegramInboundWebhookService._build_sender_name(sender),
                body_text=TelegramInboundWebhookService._extract_body_text(message_payload),
            )
            resolution.client = resolution.lead.client
            resolution.resolution_notes.append("created_new_lead")

        conversation = getattr(getattr(resolution, "matched_route", None), "conversation", None)
        if conversation is None:
            conversation = Conversation.objects.create(
                channel=CommunicationChannelCode.TELEGRAM,
                client=resolution.client,
                contact=resolution.contact,
                deal=resolution.deal,
                subject=TelegramInboundWebhookService._build_conversation_subject(message_payload=message_payload, sender=sender),
                status="active",
                requires_manual_binding=resolution.requires_manual_binding,
            )
            ConversationBindingService.bind_conversation(
                conversation=conversation,
                channel=CommunicationChannelCode.TELEGRAM,
                route_type=TelegramInboundWebhookService.ROUTE_TYPE,
                route_key=route_key,
                client=resolution.client,
                contact=resolution.contact,
                deal=resolution.deal,
                resolution_source="telegram_webhook",
            )
            if resolution.requires_manual_binding:
                conversation.requires_manual_binding = True
        else:
            conversation.client = resolution.client
            conversation.contact = resolution.contact
            conversation.deal = resolution.deal
            conversation.requires_manual_binding = resolution.requires_manual_binding

        ConversationBindingService.ensure_participant_binding(
            channel=CommunicationChannelCode.TELEGRAM,
            external_participant_key=participant_key,
            client=resolution.client,
            contact=resolution.contact,
            external_display_name=TelegramInboundWebhookService._build_sender_name(sender),
        )

        external_message_id = TelegramInboundWebhookService._build_external_message_id(
            chat_id=chat_id,
            message_id=message_payload.get("message_id"),
        )
        body_text = TelegramInboundWebhookService._extract_body_text(message_payload)
        body_preview = build_message_preview(body_text or "Сообщение Telegram")
        received_at = TelegramInboundWebhookService._extract_received_at(message_payload)

        message, created = Message.objects.get_or_create(
            channel=CommunicationChannelCode.TELEGRAM,
            external_message_id=external_message_id,
            defaults={
                "conversation": conversation,
                "direction": MessageDirection.INCOMING,
                "message_type": MessageType.TEXT,
                "status": MessageStatus.RECEIVED,
                "client": resolution.client,
                "contact": resolution.contact,
                "deal": resolution.deal,
                "external_sender_key": participant_key,
                "external_recipient_key": normalize_telegram_key(chat_id),
                "body_text": body_text,
                "body_preview": body_preview,
                "provider_message_id": str(message_payload.get("message_id") or ""),
                "provider_chat_id": chat_id,
                "provider_thread_key": route_key,
                "received_at": received_at,
            },
        )
        if created:
            CommunicationTouchService.ensure_touch_for_message(
                message=message,
                happened_at=received_at,
            )
        CommunicationTouchService.ensure_lead_for_message_touch(message=message, lead=resolution.lead)

        TelegramInboundWebhookService._refresh_conversation_snapshot(
            conversation=conversation,
            message=message,
            preview=body_preview,
            received_at=received_at,
        )
        return {
            "ok": True,
            "provider": "telegram",
            "conversation_id": conversation.pk,
            "message_id": message.pk,
            "touch_created": created,
            "duplicate_message": not created,
            "external_message_id": external_message_id,
        }

    @staticmethod
    def _refresh_conversation_snapshot(*, conversation: Conversation, message: Message, preview: str, received_at):
        conversation.last_message = message
        conversation.last_message_direction = MessageDirection.INCOMING
        conversation.last_message_preview = preview
        conversation.last_message_at = received_at
        conversation.last_incoming_at = received_at
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

    @staticmethod
    def _extract_body_text(message_payload: dict) -> str:
        for key in ("text", "caption"):
            value = str(message_payload.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _extract_received_at(message_payload: dict):
        timestamp = message_payload.get("date")
        if not timestamp:
            return timezone.now()
        try:
            return datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc)
        except (TypeError, ValueError, OSError):
            return timezone.now()

    @staticmethod
    def _build_external_message_id(*, chat_id, message_id) -> str:
        return f"telegram:{chat_id}:{message_id}"

    @staticmethod
    def _build_sender_name(sender: dict) -> str:
        first_name = str(sender.get("first_name") or "").strip()
        last_name = str(sender.get("last_name") or "").strip()
        username = str(sender.get("username") or "").strip()
        full_name = " ".join(part for part in [first_name, last_name] if part)
        return full_name or (f"@{username}" if username else "")

    @staticmethod
    def _build_conversation_subject(*, message_payload: dict, sender: dict) -> str:
        chat = message_payload.get("chat") or {}
        title = str(chat.get("title") or "").strip()
        if title:
            return title
        sender_name = TelegramInboundWebhookService._build_sender_name(sender)
        if sender_name:
            return sender_name
        return f"Telegram chat {chat.get('id')}"


class TelegramOutboundMessageService:
    ROUTE_TYPE = TelegramInboundWebhookService.ROUTE_TYPE

    @staticmethod
    def _resolve_chat_id(*, message: Message) -> str:
        route = (
            ConversationRoute.objects.filter(
                conversation=message.conversation,
                channel=CommunicationChannelCode.TELEGRAM,
                route_type=TelegramOutboundMessageService.ROUTE_TYPE,
            )
            .order_by("-is_primary", "-id")
            .first()
        )
        if route and str(route.route_key or "").strip():
            return str(route.route_key).strip()

        binding = (
            ParticipantBinding.objects.filter(
                channel=CommunicationChannelCode.TELEGRAM,
                contact=message.contact,
            )
            .order_by("-is_primary", "-id")
            .first()
        )
        if binding:
            value = str(binding.external_participant_key or "").strip()
            if value.startswith("telegram:"):
                value = value.removeprefix("telegram:")
            if re.fullmatch(r"-?\d+", value):
                return value

        raw_contact_telegram = str(getattr(getattr(message, "contact", None), "telegram", "") or "").strip().replace(" ", "")
        if re.fullmatch(r"-?\d+", raw_contact_telegram):
            return raw_contact_telegram
        return ""

    @staticmethod
    def _build_message_text(*, message: Message) -> str:
        subject = str(message.subject or "").strip()
        body = str(message.body_text or "").strip()
        chunks = []
        if subject:
            chunks.append(f"<b>{escape(subject)}</b>")
        if body:
            chunks.append(escape(body))
        if not chunks:
            chunks.append("<b>Сообщение</b>")
        return "\n\n".join(chunks)

    @staticmethod
    def _resolve_error_class(*, error_message: str) -> str:
        normalized = str(error_message or "").strip().lower()
        if not normalized:
            return ErrorClass.TEMPORARY
        if normalized in {"telegram_not_configured", "missing_telegram_chat_id"}:
            return ErrorClass.MANUAL_REQUIRED
        if "blocked" in normalized or "chat not found" in normalized or "user is deactivated" in normalized:
            return ErrorClass.PERMANENT
        if "forbidden" in normalized or "bad request" in normalized:
            return ErrorClass.PERMANENT
        return ErrorClass.TEMPORARY

    @staticmethod
    def send_message(*, message: Message) -> Message:
        if message.channel != CommunicationChannelCode.TELEGRAM:
            raise ValueError("TelegramOutboundMessageService работает только с telegram-сообщениями.")
        if message.direction != MessageDirection.OUTGOING:
            raise ValueError("Отправлять можно только исходящее сообщение.")

        chat_id = TelegramOutboundMessageService._resolve_chat_id(message=message)
        if not chat_id:
            queued_message = Message.objects.get(pk=message.pk)
            if queued_message.status != MessageStatus.QUEUED:
                MessageQueueService.enqueue_message(message=queued_message, force=True)
                queued_message.refresh_from_db()
            attempt = MessageQueueService.begin_send_attempt(message=queued_message)
            return MessageQueueService.mark_attempt_failed(
                message=queued_message,
                attempt=attempt,
                error_class=ErrorClass.MANUAL_REQUIRED,
                error_code="missing_telegram_chat_id",
                error_message="Не найден numeric chat_id для Telegram-диалога.",
                provider_response_payload={},
            )

        queued_message = Message.objects.get(pk=message.pk)
        if queued_message.status != MessageStatus.QUEUED:
            MessageQueueService.enqueue_message(message=queued_message, force=True)
            queued_message.refresh_from_db()
        attempt = MessageQueueService.begin_send_attempt(message=queued_message)
        payload = send_telegram_chat_message(
            chat_id=chat_id,
            text=TelegramOutboundMessageService._build_message_text(message=queued_message),
        )
        if payload.get("ok"):
            provider_payload = payload.get("payload") or {}
            provider_result = provider_payload.get("result") or {}
            sent_message = MessageQueueService.mark_attempt_succeeded(
                message=queued_message,
                attempt=attempt,
                provider_message_id=str(provider_result.get("message_id") or ""),
                provider_response_payload=provider_payload,
            )
            CommunicationTouchService.ensure_touch_for_message(
                message=sent_message,
                happened_at=sent_message.sent_at or timezone.now(),
            )
            sent_message.provider_chat_id = chat_id
            sent_message.external_recipient_key = normalize_telegram_key(chat_id)
            sent_message.save(update_fields=["provider_chat_id", "external_recipient_key", "updated_at"])
            conversation = sent_message.conversation
            conversation.last_message = sent_message
            conversation.last_message_direction = MessageDirection.OUTGOING
            conversation.last_message_preview = build_message_preview(sent_message.body_text or sent_message.subject or "Сообщение Telegram")
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

        error_message = str(payload.get("error") or "telegram_send_failed").strip()
        return MessageQueueService.mark_attempt_failed(
            message=queued_message,
            attempt=attempt,
            error_class=TelegramOutboundMessageService._resolve_error_class(error_message=error_message),
            error_code="telegram_send_failed",
            error_message=error_message,
            provider_response_payload=payload,
        )

    @staticmethod
    def send_due_messages(*, limit: int = 50) -> dict:
        now = timezone.now()
        queryset = (
            Message.objects.filter(
                channel=CommunicationChannelCode.TELEGRAM,
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
            processed_message = TelegramOutboundMessageService.send_message(message=message)
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
