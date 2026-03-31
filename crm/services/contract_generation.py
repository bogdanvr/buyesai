from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from xml.sax.saxutils import escape

from crm.models import Client, Contact, SettlementContract


DEFAULT_CONTRACT_TITLE = "Договор об оказании услуг"
DEFAULT_WARRANTY_DAYS = 31
DEFAULT_CLAIM_RESPONSE_DAYS = 5
DEFAULT_TERMINATION_NOTICE_DAYS = 5
SERVICE_AGREEMENT_TEMPLATE_CODE = "service_agreement"
SERVICE_AGREEMENT_TEMPLATE_PATH = Path(settings.BASE_DIR) / "crm" / "resources" / "contracts" / "service-agreement-template.docx"

RUSSIAN_MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _format_date_human(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return f"«{value.day:02d}» {RUSSIAN_MONTHS.get(value.month, '')} {value.year} г."


def _format_decimal(value: Decimal | int | float | str) -> str:
    normalized = Decimal(value or 0).quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _contract_display_name(contract: SettlementContract) -> str:
    number = _normalize_text(contract.number)
    title = _normalize_text(contract.title) or DEFAULT_CONTRACT_TITLE
    if number:
        return f"Договор № {number} от {contract.start_date.strftime('%d.%m.%Y') if contract.start_date else timezone.localdate().strftime('%d.%m.%Y')}.docx"
    return f"{title}.docx"


def _select_executor_company(explicit_id: int | None = None) -> Client:
    queryset = Client.objects.filter(company_type=Client.CompanyType.OWN, is_active=True).order_by("id")
    if explicit_id:
        executor_company = queryset.filter(pk=explicit_id).first()
        if executor_company is not None:
            return executor_company
    executor_company = queryset.first()
    if executor_company is None:
        raise ValidationError({"executor_company": "Не найдена собственная организация для генерации договора."})
    return executor_company


def _resolve_contact_for_company(company: Client) -> Contact | None:
    work_rules = company.work_rules if isinstance(company.work_rules, dict) else {}
    decision_maker_id = work_rules.get("decision_maker_contact")
    if decision_maker_id not in (None, "", 0, "0"):
        try:
            normalized_id = int(decision_maker_id)
        except (TypeError, ValueError):
            normalized_id = None
        if normalized_id:
            contact = Contact.objects.filter(pk=normalized_id, client_id=company.pk).first()
            if contact is not None:
                return contact
    return Contact.objects.filter(client_id=company.pk).order_by("-is_primary", "last_name", "first_name", "id").first()


def _company_representative(company: Client, *, default_position: str, default_name: str) -> tuple[str, str]:
    contact = _resolve_contact_for_company(company)
    if contact is None:
        return default_position, default_name
    full_name = _normalize_text(f"{contact.first_name} {contact.last_name}")
    position = _normalize_text(contact.position) or default_position
    if not full_name:
        full_name = default_name
    return position, full_name


def _company_name(company: Client) -> str:
    return _normalize_text(company.legal_name) or _normalize_text(company.name) or f"Компания #{company.pk}"


def _company_address(company: Client) -> str:
    return _normalize_text(company.address) or _normalize_text(company.actual_address) or "Не указан"


def _company_city(company: Client) -> str:
    raw_address = _company_address(company)
    if not raw_address or raw_address == "Не указан":
        return "__________"
    for pattern in (
        r"(?:^|,\s*)г\.?\s*([^,;]+)",
        r"(?:^|,\s*)город\s+([^,;]+)",
    ):
        match = re.search(pattern, raw_address, flags=re.IGNORECASE)
        if match:
            city = _normalize_text(match.group(1))
            if city:
                return city
    first_chunk = _normalize_text(raw_address.split(",")[0])
    if first_chunk and len(first_chunk) <= 60:
        return re.sub(r"^(адрес:?)\s*", "", first_chunk, flags=re.IGNORECASE).strip() or "__________"
    return "__________"


def _company_account(company: Client) -> str:
    return _normalize_text(company.settlement_account) or _normalize_text(company.iban) or "Не указан"


def _company_kpp(company: Client) -> str:
    return _normalize_text(company.kpp) or "-"


def _company_inn(company: Client) -> str:
    return _normalize_text(company.inn) or "-"


def _company_ogrn(company: Client) -> str:
    return _normalize_text(company.ogrn) or "-"


def _company_bik(company: Client) -> str:
    return _normalize_text(company.bik) or "-"


def _company_correspondent_account(company: Client) -> str:
    return _normalize_text(company.correspondent_account) or "-"


def _company_bank(company: Client) -> str:
    return _normalize_text(company.bank_name) or "Не указан"


def _company_email(company: Client) -> str:
    return _normalize_text(company.email) or "-"


def _company_phone(company: Client) -> str:
    return _normalize_text(company.phone) or "-"


def _company_signature_label(company: Client) -> str:
    contact = _resolve_contact_for_company(company)
    full_name = _normalize_text(f"{getattr(contact, 'first_name', '')} {getattr(contact, 'last_name', '')}")
    return full_name or "_____________"


def _replace_text(xml: str, old: str, new: str, *, count: int = -1) -> str:
    escaped_new = escape(str(new))
    if count < 0:
        return xml.replace(old, escaped_new)
    return xml.replace(old, escaped_new, count)


def _next_contract_number() -> str:
    numbers = SettlementContract.objects.exclude(number="").values_list("number", flat=True)
    max_numeric = 0
    for value in numbers:
        digits = re.sub(r"\D+", "", str(value or ""))
        if not digits:
            continue
        max_numeric = max(max_numeric, int(digits))
    if max_numeric:
        return str(max_numeric + 1)
    return str(SettlementContract.objects.count() + 1)


def _build_contract_docx(contract: SettlementContract, executor_company: Client) -> bytes:
    if not SERVICE_AGREEMENT_TEMPLATE_PATH.exists():
        raise ValidationError({"template": "Шаблон договора не найден в проекте."})

    customer_company = contract.client
    contract_date = contract.start_date or timezone.localdate()
    customer_position, customer_name = _company_representative(
        customer_company,
        default_position="уполномоченного представителя",
        default_name="_____________",
    )
    executor_position, executor_name = _company_representative(
        executor_company,
        default_position="генерального директора",
        default_name="_____________",
    )

    with ZipFile(SERVICE_AGREEMENT_TEMPLATE_PATH, "r") as source_zip:
        xml = source_zip.read("word/document.xml").decode("utf-8")

        xml = _replace_text(xml, "[вставить номер]", _normalize_text(contract.number) or _next_contract_number(), count=1)
        xml = _replace_text(xml, "[вставить город]", _company_city(executor_company), count=1)
        xml = _replace_text(xml, "«___» __________ 20__ г.", _format_date_human(contract_date), count=1)

        xml = _replace_text(xml, "[Полное фирменное наименование Заказчика]", _company_name(customer_company), count=1)
        xml = _replace_text(xml, "[ФИО, должность]", f"{customer_position} {customer_name}".strip(), count=1)
        xml = _replace_text(xml, "[Устава / доверенности]", "Устава", count=1)

        xml = _replace_text(xml, "[Полное фирменное наименование Исполнителя]", _company_name(executor_company), count=1)
        xml = _replace_text(xml, "[ФИО, должность]", f"{executor_position} {executor_name}".strip(), count=1)
        xml = _replace_text(xml, "[Устава / доверенности]", "Устава", count=1)

        xml = _replace_text(xml, "аванс в размере [___] % стоимости этапа", f"аванс в размере {_format_decimal(contract.advance_percent or 0)} % стоимости этапа", count=1)
        xml = _replace_text(xml, "составляет [вставить сумму] рублей.", f"составляет {_format_decimal(contract.hourly_rate or 0)} рублей.", count=1)
        xml = _replace_text(xml, "составляет [___] календарных дней", f"составляет {int(contract.warranty_days or DEFAULT_WARRANTY_DAYS)} календарных дней", count=1)
        xml = _replace_text(xml, "не менее чем за [___] календарных дней.", f"не менее чем за {int(contract.termination_notice_days or DEFAULT_TERMINATION_NOTICE_DAYS)} календарных дней.", count=1)
        xml = _replace_text(xml, "составляет [___] календарных дней с даты ее получения.", f"составляет {int(contract.claim_response_days or DEFAULT_CLAIM_RESPONSE_DAYS)} календарных дней с даты ее получения.", count=1)

        customer_requisites = [
            ("Полное наименование: [___]", f"Полное наименование: {_company_name(customer_company)}"),
            ("Адрес: [___]", f"Адрес: {_company_address(customer_company)}"),
            ("ИНН / КПП: [___]", f"ИНН / КПП: {_company_inn(customer_company)} / {_company_kpp(customer_company)}"),
            ("ОГРН: [___]", f"ОГРН: {_company_ogrn(customer_company)}"),
            ("р/с: [___]", f"р/с: {_company_account(customer_company)}"),
            ("в [___]", f"в {_company_bank(customer_company)}"),
            ("БИК: [___]", f"БИК: {_company_bik(customer_company)}"),
            ("к/с: [___]", f"к/с: {_company_correspondent_account(customer_company)}"),
            ("Email: [___]", f"Email: {_company_email(customer_company)}"),
            ("Тел.: [___]", f"Тел.: {_company_phone(customer_company)}"),
        ]
        for old, new in customer_requisites:
            xml = _replace_text(xml, old, new, count=1)

        executor_requisites = [
            ("Полное наименование: [___]", f"Полное наименование: {_company_name(executor_company)}"),
            ("Адрес: [___]", f"Адрес: {_company_address(executor_company)}"),
            ("ИНН / КПП: [___]", f"ИНН / КПП: {_company_inn(executor_company)} / {_company_kpp(executor_company)}"),
            ("ОГРН: [___]", f"ОГРН: {_company_ogrn(executor_company)}"),
            ("р/с: [___]", f"р/с: {_company_account(executor_company)}"),
            ("в [___]", f"в {_company_bank(executor_company)}"),
            ("БИК: [___]", f"БИК: {_company_bik(executor_company)}"),
            ("к/с: [___]", f"к/с: {_company_correspondent_account(executor_company)}"),
            ("Email: [___]", f"Email: {_company_email(executor_company)}"),
            ("Тел.: [___]", f"Тел.: {_company_phone(executor_company)}"),
        ]
        for old, new in executor_requisites:
            xml = _replace_text(xml, old, new, count=1)

        xml = _replace_text(xml, "________________ /_____________/", f"________________ /{_company_signature_label(customer_company)}/", count=1)
        xml = _replace_text(xml, "________________ /_____________/", f"________________ /{_company_signature_label(executor_company)}/", count=1)

        from io import BytesIO

        result = BytesIO()
        with ZipFile(result, "w", compression=ZIP_DEFLATED) as target_zip:
            for item in source_zip.infolist():
                data = xml.encode("utf-8") if item.filename == "word/document.xml" else source_zip.read(item.filename)
                target_zip.writestr(item, data)
        return result.getvalue()


@transaction.atomic
def generate_service_agreement_contract(
    *,
    client: Client,
    advance_percent: Decimal | int | float | str,
    hourly_rate: Decimal | int | float | str,
    warranty_days: int = DEFAULT_WARRANTY_DAYS,
    claim_response_days: int = DEFAULT_CLAIM_RESPONSE_DAYS,
    termination_notice_days: int = DEFAULT_TERMINATION_NOTICE_DAYS,
) -> SettlementContract:
    executor_company = _select_executor_company()
    contract = SettlementContract.objects.create(
        client=client,
        title=DEFAULT_CONTRACT_TITLE,
        number=_next_contract_number(),
        currency=_normalize_text(client.currency).upper() or "RUB",
        advance_percent=Decimal(advance_percent or 0).quantize(Decimal("0.01")),
        hourly_rate=Decimal(hourly_rate or 0).quantize(Decimal("0.01")),
        warranty_days=int(warranty_days or DEFAULT_WARRANTY_DAYS),
        claim_response_days=int(claim_response_days or DEFAULT_CLAIM_RESPONSE_DAYS),
        termination_notice_days=int(termination_notice_days or DEFAULT_TERMINATION_NOTICE_DAYS),
        start_date=timezone.localdate(),
        generator_payload={
            "template_code": SERVICE_AGREEMENT_TEMPLATE_CODE,
            "executor_company_id": executor_company.pk,
        },
    )
    refresh_generated_service_agreement(contract)
    return contract


def refresh_generated_service_agreement(contract: SettlementContract) -> SettlementContract:
    payload = contract.generator_payload if isinstance(contract.generator_payload, dict) else {}
    executor_company = _select_executor_company(payload.get("executor_company_id"))
    document_bytes = _build_contract_docx(contract, executor_company)
    filename = _contract_display_name(contract)
    contract.original_name = filename
    contract.generator_payload = {
        **payload,
        "template_code": SERVICE_AGREEMENT_TEMPLATE_CODE,
        "executor_company_id": executor_company.pk,
        "generated_at": timezone.now().isoformat(),
    }
    contract.file.save(filename, ContentFile(document_bytes), save=False)
    contract.save(update_fields=[
        "title",
        "number",
        "currency",
        "advance_percent",
        "hourly_rate",
        "warranty_days",
        "claim_response_days",
        "termination_notice_days",
        "start_date",
        "generator_payload",
        "original_name",
        "file",
        "updated_at",
    ])
    return contract
