import logging
from typing import Iterable

from crm.models import Client, Contact, Deal, Lead
from integrations.models import TelephonyProviderAccount, TelephonyProvider, TelephonyUserMapping


logger = logging.getLogger(__name__)


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return ""
    if len(digits) == 10:
        digits = f"7{digits}"
    elif len(digits) == 11 and digits.startswith("8"):
        digits = f"7{digits[1:]}"
    return digits[:16]


def get_novofon_account(*, create: bool = True) -> TelephonyProviderAccount | None:
    queryset = TelephonyProviderAccount.objects.filter(provider=TelephonyProvider.NOVOFON)
    account = queryset.first()
    if account is not None or not create:
        return account
    return TelephonyProviderAccount.objects.create(provider=TelephonyProvider.NOVOFON)


def build_webhook_url(account: TelephonyProviderAccount) -> str:
    from django.conf import settings

    base_url = str(getattr(settings, "CRM_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    path = str(account.webhook_path or "").strip() or "/api/integrations/novofon/webhook/"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}" if base_url else path


def resolve_novofon_mapping(*, account: TelephonyProviderAccount, crm_user=None, employee_id: str = "", extension: str = "") -> TelephonyUserMapping | None:
    queryset = TelephonyUserMapping.objects.filter(provider_account=account, is_active=True).select_related("crm_user")
    if crm_user is not None:
        mapping = queryset.filter(crm_user=crm_user).first()
        if mapping is not None:
            return mapping
    normalized_employee_id = str(employee_id or "").strip()
    if normalized_employee_id:
        mapping = queryset.filter(novofon_employee_id=normalized_employee_id).first()
        if mapping is not None:
            return mapping
    normalized_extension = str(extension or "").strip()
    if normalized_extension:
        return queryset.filter(novofon_extension=normalized_extension).first()
    return None


def _filter_by_normalized_phone(items: Iterable, *, attr_name: str, normalized_phone: str):
    results = []
    for item in items:
        normalized_value = normalize_phone(getattr(item, attr_name, ""))
        if normalized_value and normalized_value == normalized_phone:
            results.append(item)
    return results


def _choose_company_contacts(normalized_phone: str) -> list[Contact]:
    contacts = Contact.objects.select_related("client").exclude(phone="").order_by("-is_primary", "id")
    return _filter_by_normalized_phone(contacts, attr_name="phone", normalized_phone=normalized_phone)


def _choose_companies(normalized_phone: str) -> list[Client]:
    companies = Client.objects.exclude(phone="").order_by("id")
    return _filter_by_normalized_phone(companies, attr_name="phone", normalized_phone=normalized_phone)


def _choose_leads(normalized_phone: str) -> list[Lead]:
    return list(
        Lead.objects.select_related("assigned_to", "client", "status")
        .filter(phone_normalized=normalized_phone)
        .order_by("status__is_final", "-created_at", "-id")
    )


def _choose_open_deal(*, company: Client | None = None, lead: Lead | None = None) -> Deal | None:
    queryset = Deal.objects.select_related("stage", "client", "owner", "lead")
    if company is not None:
        queryset = queryset.filter(client=company)
    elif lead is not None:
        queryset = queryset.filter(lead=lead)
    else:
        return None
    return queryset.filter(stage__is_final=False).order_by("close_date", "-created_at", "-id").first()


def resolve_call_binding(*, account: TelephonyProviderAccount, phone_normalized: str) -> dict:
    if not phone_normalized:
        return {
            "contact": None,
            "company": None,
            "lead": None,
            "deal": None,
            "was_ambiguous": False,
        }

    contacts = _choose_company_contacts(phone_normalized)
    companies = _choose_companies(phone_normalized)
    leads = _choose_leads(phone_normalized)

    primary_contact = contacts[0] if contacts else None
    primary_company = primary_contact.client if primary_contact is not None else (companies[0] if companies else None)
    primary_lead = leads[0] if leads else None

    deal = None
    if primary_company is not None:
        deal = _choose_open_deal(company=primary_company)
    if deal is None and primary_lead is not None:
        deal = _choose_open_deal(lead=primary_lead)
    if deal is None and not account.link_calls_to_open_deal_only and primary_company is not None:
        deal = (
            Deal.objects.select_related("stage", "client", "owner", "lead")
            .filter(client=primary_company)
            .order_by("-created_at", "-id")
            .first()
        )

    was_ambiguous = len(contacts) > 1 or len(companies) > 1 or len(leads) > 1
    if was_ambiguous:
        logger.warning(
            "Novofon binding ambiguity. phone=%s contacts=%s companies=%s leads=%s",
            phone_normalized,
            len(contacts),
            len(companies),
            len(leads),
        )

    return {
        "contact": primary_contact,
        "company": primary_company,
        "lead": primary_lead,
        "deal": deal,
        "was_ambiguous": was_ambiguous,
    }
