from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from crm.models import Client, Contact, Deal, Lead
from crm.models.lead import normalize_lead_phone
from main.tracking import (
    build_tracking_sources,
    get_primary_tracking_source,
    sync_lead_tracking_data,
)


def _text_or_empty(value) -> str:
    return str(value or "").strip()


def _merge_dicts(base: dict | None, extra: dict | None) -> dict:
    result = dict(base) if isinstance(base, dict) else {}
    if isinstance(extra, dict):
        for key, value in extra.items():
            result[key] = value
    return result


def _extract_company_profile(payload: dict) -> dict:
    company_data = payload.get("company_data")
    profile = company_data if isinstance(company_data, dict) else {}

    name = (
        _text_or_empty(profile.get("name"))
        or _text_or_empty(payload.get("company_name"))
        or _text_or_empty(payload.get("company"))
    )
    legal_name = _text_or_empty(profile.get("legal_name")) or _text_or_empty(payload.get("company_legal_name"))
    inn = _text_or_empty(profile.get("inn")) or _text_or_empty(payload.get("company_inn"))
    address = _text_or_empty(profile.get("address")) or _text_or_empty(payload.get("company_address"))
    industry = (
        _text_or_empty(profile.get("industry"))
        or _text_or_empty(payload.get("company_industry"))
        or _text_or_empty(payload.get("industry"))
    )
    okved = _text_or_empty(profile.get("okved")) or _text_or_empty(payload.get("company_okved"))
    if not industry and okved:
        industry = f"ОКВЭД {okved}"

    raw_okveds = profile.get("okveds")
    okveds = []
    if isinstance(raw_okveds, list):
        for entry in raw_okveds:
            if not isinstance(entry, dict):
                continue
            code = _text_or_empty(entry.get("code") or entry.get("okved"))
            okved_name = _text_or_empty(entry.get("name") or entry.get("title"))
            if not code and not okved_name:
                continue
            okveds.append(
                {
                    "code": code,
                    "name": okved_name,
                    "main": bool(entry.get("main")),
                }
            )
    if okved and not okveds:
        okveds.append({"code": okved, "name": industry, "main": True})

    director_data = profile.get("director") if isinstance(profile.get("director"), dict) else {}
    director = {
        "name": _text_or_empty(director_data.get("name")),
        "position": _text_or_empty(director_data.get("position")),
        "phone": _text_or_empty(director_data.get("phone")),
        "email": _text_or_empty(director_data.get("email")),
    }

    return {
        "name": name,
        "legal_name": legal_name,
        "inn": inn,
        "address": address,
        "industry": industry,
        "okved": okved,
        "okveds": okveds,
        "director": director,
    }


def _split_full_name(full_name: str) -> tuple[str, str]:
    normalized = " ".join(str(full_name or "").split()).strip()
    if not normalized:
        return "", ""
    parts = normalized.split(" ")
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _upsert_director_contact(*, client: Client, director: dict) -> None:
    full_name = _text_or_empty(director.get("name"))
    if not full_name:
        return

    first_name, last_name = _split_full_name(full_name)
    phone = _text_or_empty(director.get("phone"))
    position = _text_or_empty(director.get("position"))
    email = _text_or_empty(director.get("email"))

    contact = None
    if first_name or last_name:
        contact = (
            Contact.objects.filter(
                client=client,
                first_name__iexact=first_name,
                last_name__iexact=last_name,
            )
            .order_by("id")
            .first()
        )
    if contact is None and phone:
        contact = Contact.objects.filter(client=client, phone=phone).order_by("id").first()

    if contact is None:
        contact = Contact.objects.create(
            client=client,
            first_name=first_name,
            last_name=last_name,
            position=position,
            phone=phone,
            email=email,
            is_primary=not Contact.objects.filter(client=client, is_primary=True).exists(),
        )
        return

    update_fields = []
    if first_name and contact.first_name != first_name:
        contact.first_name = first_name
        update_fields.append("first_name")
    if last_name and contact.last_name != last_name:
        contact.last_name = last_name
        update_fields.append("last_name")
    if position and contact.position != position:
        contact.position = position
        update_fields.append("position")
    if phone and contact.phone != phone:
        contact.phone = phone
        update_fields.append("phone")
    if email and contact.email != email:
        contact.email = email
        update_fields.append("email")
    if update_fields:
        update_fields.append("updated_at")
        contact.save(update_fields=update_fields)


def _find_duplicate_lead(*, payload: dict, website_session=None) -> Lead | None:
    if website_session is not None:
        existing = (
            Lead.objects.filter(website_session=website_session)
            .order_by("-updated_at", "-id")
            .first()
        )
        if existing is not None:
            return existing

    external_id = _text_or_empty(payload.get("external_id"))
    if external_id:
        existing = Lead.objects.filter(external_id=external_id).order_by("-updated_at", "-id").first()
        if existing is not None:
            return existing

    normalized_phone = normalize_lead_phone(payload.get("phone"))
    if not normalized_phone:
        return None

    active_match = (
        Lead.objects.filter(phone_normalized=normalized_phone)
        .exclude(status__code__in=("converted", "archived"))
        .order_by("-updated_at", "-id")
        .first()
    )
    if active_match is not None:
        return active_match

    return (
        Lead.objects.filter(phone_normalized=normalized_phone)
        .order_by("-updated_at", "-id")
        .first()
    )


def _merge_duplicate_lead(
    *,
    lead: Lead,
    form_type: str,
    payload: dict,
    source=None,
    created_by=None,
    website_session=None,
    client: Client | None = None,
) -> Lead:
    update_fields = []

    external_id = _text_or_empty(payload.get("external_id"))
    if external_id and lead.external_id != external_id:
        lead.external_id = external_id
        update_fields.append("external_id")

    title = _text_or_empty(payload.get("title")) or f"Лид из формы {form_type}"
    if title and not _text_or_empty(lead.title):
        lead.title = title
        update_fields.append("title")

    name = _text_or_empty(payload.get("name"))
    if name and not _text_or_empty(lead.name):
        lead.name = name
        update_fields.append("name")

    phone = _text_or_empty(payload.get("phone"))
    if phone and _text_or_empty(lead.phone) != phone:
        lead.phone = phone
        update_fields.append("phone")

    email = _text_or_empty(payload.get("email"))
    if email and not _text_or_empty(lead.email):
        lead.email = email
        update_fields.append("email")

    company_name = _text_or_empty(payload.get("company"))
    if company_name and not _text_or_empty(lead.company):
        lead.company = company_name
        update_fields.append("company")

    if client is not None and lead.client_id != client.id:
        lead.client = client
        update_fields.append("client")

    if created_by is not None and lead.created_by_id is None:
        lead.created_by = created_by
        update_fields.append("created_by")

    if website_session is not None and lead.website_session_id is None:
        lead.website_session = website_session
        update_fields.append("website_session")

    merged_payload = _merge_dicts(getattr(lead, "payload", {}), payload)
    if lead.payload != merged_payload:
        lead.payload = merged_payload
        update_fields.append("payload")

    incoming_utm = payload.get("utm_data") if isinstance(payload.get("utm_data"), dict) else {}
    merged_utm = _merge_dicts(getattr(lead, "utm_data", {}), incoming_utm)
    if lead.utm_data != merged_utm:
        lead.utm_data = merged_utm
        update_fields.append("utm_data")

    effective_primary_source = get_primary_tracking_source(website_session, source)
    if effective_primary_source is not None and lead.source_id is None:
        lead.source = effective_primary_source
        update_fields.append("source")

    if update_fields:
        update_fields.append("updated_at")
        lead.save(update_fields=update_fields)

    if website_session is not None:
        if lead.website_session_id in (None, website_session.id):
            sync_lead_tracking_data(lead, website_session, source)
        else:
            sources_to_add = build_tracking_sources(website_session)
            if source is not None:
                sources_to_add.append(source)
            if effective_primary_source is not None:
                sources_to_add.append(effective_primary_source)
            if sources_to_add:
                lead.sources.add(*sources_to_add)
    elif source is not None or effective_primary_source is not None:
        sources_to_add = []
        if source is not None:
            sources_to_add.append(source)
        if effective_primary_source is not None:
            sources_to_add.append(effective_primary_source)
        if sources_to_add:
            lead.sources.add(*sources_to_add)

    return lead


@transaction.atomic
def create_lead_from_payload(
    *,
    form_type: str,
    payload: dict,
    source=None,
    created_by=None,
    website_session=None,
) -> Lead:
    company_profile = _extract_company_profile(payload)
    company_name = company_profile["name"]
    company_inn = company_profile["inn"]

    client = None
    if company_inn:
        client = Client.objects.filter(inn=company_inn).order_by("id").first()
    if client is None and company_name:
        client = Client.objects.filter(name__iexact=company_name).order_by("id").first()

    if client is None and company_name:
        client = Client.objects.create(
            name=company_name,
            legal_name=company_profile["legal_name"],
            inn=company_inn or None,
            address=company_profile["address"],
            industry=company_profile["industry"],
            okved=company_profile["okved"],
            okveds=company_profile["okveds"],
            source=source,
        )
    elif client is not None:
        update_fields = []
        if source and client.source_id is None:
            client.source = source
            update_fields.append("source")
        if company_name and client.name != company_name:
            client.name = company_name
            update_fields.append("name")
        if company_profile["legal_name"] and client.legal_name != company_profile["legal_name"]:
            client.legal_name = company_profile["legal_name"]
            update_fields.append("legal_name")
        if company_inn and client.inn != company_inn:
            inn_taken = Client.objects.filter(inn=company_inn).exclude(pk=client.pk).exists()
            if not inn_taken:
                client.inn = company_inn
                update_fields.append("inn")
        if company_profile["address"] and client.address != company_profile["address"]:
            client.address = company_profile["address"]
            update_fields.append("address")
        if company_profile["industry"] and client.industry != company_profile["industry"]:
            client.industry = company_profile["industry"]
            update_fields.append("industry")
        if company_profile["okved"] and client.okved != company_profile["okved"]:
            client.okved = company_profile["okved"]
            update_fields.append("okved")
        if company_profile["okveds"] and client.okveds != company_profile["okveds"]:
            client.okveds = company_profile["okveds"]
            update_fields.append("okveds")
        if update_fields:
            update_fields.append("updated_at")
            client.save(update_fields=update_fields)

    if client is not None:
        _upsert_director_contact(client=client, director=company_profile["director"])

    duplicate_lead = _find_duplicate_lead(payload=payload, website_session=website_session)
    if duplicate_lead is not None:
        return _merge_duplicate_lead(
            lead=duplicate_lead,
            form_type=form_type,
            payload=payload,
            source=source,
            created_by=created_by,
            website_session=website_session,
            client=client,
        )

    lead = Lead.objects.create(
        external_id=_text_or_empty(payload.get("external_id")),
        title=f"Лид из формы {form_type}",
        name=_text_or_empty(payload.get("name")),
        phone=_text_or_empty(payload.get("phone")),
        email=_text_or_empty(payload.get("email")),
        company=company_name,
        client=client,
        source=source,
        website_session=website_session,
        payload=payload,
        utm_data=payload.get("utm_data") if isinstance(payload.get("utm_data"), dict) else {},
        created_by=created_by,
    )
    if website_session is not None:
        sync_lead_tracking_data(lead, website_session, source)
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
            description=lead.description or "",
            source=lead.source,
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
            description=lead.description or "",
            source=lead.source,
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
