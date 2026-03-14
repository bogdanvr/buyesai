from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.models import Client, Deal, Lead


@transaction.atomic
def create_lead_from_payload(*, form_type: str, payload: dict, source=None, created_by=None) -> Lead:
    company_name = str(payload.get("company") or "").strip()
    client = None
    if company_name:
        client = Client.objects.filter(name__iexact=company_name).order_by("id").first()
        if client is None:
            client = Client.objects.create(name=company_name, source=source)

    lead = Lead.objects.create(
        title=f"Лид из формы {form_type}",
        name=str(payload.get("name") or ""),
        phone=str(payload.get("phone") or ""),
        email=str(payload.get("email") or ""),
        company=company_name,
        client=client,
        source=source,
        payload=payload,
        utm_data=payload.get("utm_data") if isinstance(payload.get("utm_data"), dict) else {},
        created_by=created_by,
    )
    return lead


@transaction.atomic
def assign_lead_to_client(*, lead: Lead, client: Client) -> Lead:
    lead.client = client
    if not lead.company:
        lead.company = client.name
    lead.save(update_fields=["client", "company", "updated_at"])
    return lead


@transaction.atomic
def convert_lead_to_deal(
    *,
    lead: Lead,
    client: Client | None = None,
    stage=None,
    amount: Decimal | int | float = 0,
    owner=None,
) -> Deal:
    target_client = client or lead.client
    company_name = (lead.company or "").strip()
    if target_client is None and company_name:
        target_client = Client.objects.create(
            name=company_name,
            source=lead.source,
        )
    try:
        deal = Deal.objects.create(
            title=lead.title or f"Сделка из лида #{lead.id}",
            client=target_client,
            lead=lead,
            stage=stage,
            amount=amount,
            owner=owner,
        )
    except IntegrityError:
        # Backward-compatibility path for instances where DB schema has not
        # yet applied optional deal.client migration.
        if target_client is not None:
            raise
        fallback_name = lead.company or lead.name or lead.title or f"Клиент из лида #{lead.id}"
        target_client = Client.objects.create(name=fallback_name.strip(), source=lead.source)
        deal = Deal.objects.create(
            title=lead.title or f"Сделка из лида #{lead.id}",
            client=target_client,
            lead=lead,
            stage=stage,
            amount=amount,
            owner=owner,
        )
    lead.client = target_client
    lead.converted_at = timezone.now()
    lead.save(update_fields=["client", "converted_at", "updated_at"])
    return deal
