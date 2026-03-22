from dataclasses import dataclass, field
from typing import Iterable

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.models import Client, Contact, Deal
from crm_communications.models import (
    CommunicationChannelCode,
    Conversation,
    ConversationRoute,
    ParticipantBinding,
)


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


@dataclass
class ConversationResolution:
    client: Client | None = None
    contact: Contact | None = None
    deal: Deal | None = None
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

        if resolution.client is None and resolution.contact is not None:
            resolution.client = resolution.contact.client

        active_deals = get_active_deals_for_client(client=resolution.client)
        if resolution.deal is None:
            if len(active_deals) == 1:
                resolution.deal = active_deals[0]
                resolution.resolution_notes.append("matched_by_single_active_deal")
            elif len(active_deals) > 1:
                resolution.requires_manual_binding = True
                resolution.resolution_notes.append("requires_manual_binding")

        return resolution


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
