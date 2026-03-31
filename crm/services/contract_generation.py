from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from io import BytesIO
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
DEFAULT_OFFER_CONTRACT_TITLE = "Договор-оферта"
DEFAULT_WARRANTY_DAYS = 31
DEFAULT_CLAIM_RESPONSE_DAYS = 5
DEFAULT_TERMINATION_NOTICE_DAYS = 5
DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS = 5
DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS = 5
DEFAULT_OFFER_FINAL_PAYMENT_DAYS = 5
DEFAULT_OFFER_ACCEPTANCE_DAYS = 5
DEFAULT_OFFER_PENALTY_RATE = Decimal("0.10")
DEFAULT_OFFER_PENALTY_CAP_PERCENT = Decimal("10.00")

SERVICE_AGREEMENT_TEMPLATE_CODE = "service_agreement"
OFFER_AGREEMENT_TEMPLATE_CODE = "offer_agreement"
GENERATED_CONTRACT_TEMPLATE_CODES = {
    SERVICE_AGREEMENT_TEMPLATE_CODE,
    OFFER_AGREEMENT_TEMPLATE_CODE,
}

SERVICE_AGREEMENT_TEMPLATE_PATH = Path(settings.BASE_DIR) / "crm" / "resources" / "contracts" / "service-agreement-template.docx"
OFFER_AGREEMENT_TEMPLATE_PATH = Path(settings.BASE_DIR) / "crm" / "resources" / "contracts" / "offer-agreement-template.docx"

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


def _template_code(payload: dict | None) -> str:
    value = _normalize_text((payload or {}).get("template_code"))
    return value if value in GENERATED_CONTRACT_TEMPLATE_CODES else SERVICE_AGREEMENT_TEMPLATE_CODE


def _default_contract_title(template_code: str) -> str:
    return DEFAULT_OFFER_CONTRACT_TITLE if template_code == OFFER_AGREEMENT_TEMPLATE_CODE else DEFAULT_CONTRACT_TITLE


def _format_date_human(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return f"«{value.day:02d}» {RUSSIAN_MONTHS.get(value.month, '')} {value.year} г."


def _format_date_human_plain(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return f"{value.day:02d} {RUSSIAN_MONTHS.get(value.month, '')} {value.year} г."


def _format_decimal(value: Decimal | int | float | str) -> str:
    normalized = Decimal(value or 0).quantize(Decimal("0.01"))
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _decimal_or_default(value: Decimal | int | float | str | None, default: Decimal) -> Decimal:
    if value in (None, ""):
        return default
    return Decimal(str(value).replace(",", ".")).quantize(Decimal("0.01"))


def _serialize_decimal(value: Decimal | int | float | str | None, default: Decimal) -> str:
    normalized = _decimal_or_default(value, default)
    return format(normalized, "f")


def _int_or_default(value: int | str | None, default: int) -> int:
    if value in (None, ""):
        return int(default)
    return int(value)


def _payload_int(payload: dict, key: str, default: int) -> int:
    return _int_or_default(payload.get(key), default)


def _payload_decimal(payload: dict, key: str, default: Decimal) -> Decimal:
    return _decimal_or_default(payload.get(key), default)


def _payload_date(payload: dict, key: str) -> date | None:
    value = payload.get(key)
    if isinstance(value, date):
        return value
    value = _normalize_text(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _contract_display_name(contract: SettlementContract) -> str:
    payload = contract.generator_payload if isinstance(contract.generator_payload, dict) else {}
    template_code = _template_code(payload)
    number = _normalize_text(contract.number)
    title = _normalize_text(contract.title) or _default_contract_title(template_code)
    contract_date = contract.start_date or timezone.localdate()
    if number and template_code == OFFER_AGREEMENT_TEMPLATE_CODE:
        return f"{title} № {number} от {contract_date.strftime('%d.%m.%Y')}.docx"
    if number and template_code == SERVICE_AGREEMENT_TEMPLATE_CODE:
        return f"Договор № {number} от {contract_date.strftime('%d.%m.%Y')}.docx"
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


def _resolve_contract_contact(company: Client, explicit_contact_id: int | None = None) -> Contact | None:
    if explicit_contact_id:
        contact = Contact.objects.filter(pk=explicit_contact_id, client_id=company.pk).first()
        if contact is not None:
            return contact
    return _resolve_contact_for_company(company)


def _company_representative(company: Client, *, default_position: str, default_name: str, contact: Contact | None = None) -> tuple[str, str]:
    contact = contact or _resolve_contact_for_company(company)
    if contact is None:
        return default_position, default_name
    full_name = _normalize_text(f"{contact.first_name} {contact.last_name}")
    position = _normalize_text(contact.position) or default_position
    if not full_name:
        full_name = default_name
    return position, full_name


def _company_name(company: Client) -> str:
    return _normalize_text(company.legal_name) or _normalize_text(company.name) or f"Компания #{company.pk}"


def _company_offer_executor_display_name(company: Client) -> str:
    legal_name = _normalize_text(company.legal_name)
    if not legal_name:
        return _company_name(company)
    full_match = re.match(r"^общество\s+с\s+ограниченной\s+ответственностью\b", legal_name, flags=re.IGNORECASE)
    if full_match:
        suffix = legal_name[full_match.end():].strip()
        return suffix or legal_name
    abbreviated_match = re.match(r"^ооо\b", legal_name, flags=re.IGNORECASE)
    if abbreviated_match:
        suffix = legal_name[abbreviated_match.end():].strip()
        return suffix or legal_name
    return legal_name


def _company_address(company: Client) -> str:
    return _normalize_text(company.address) or _normalize_text(company.actual_address) or "Не указан"


def _company_city(company: Client) -> str:
    raw_address = _company_address(company)
    if not raw_address or raw_address == "Не указан":
        return "__________"
    chunks = [
        re.sub(r"^\d{5,6}\s*", "", _normalize_text(chunk))
        for chunk in raw_address.split(",")
    ]
    chunks = [chunk for chunk in chunks if chunk]
    for chunk in chunks:
        match = re.match(r"^(?:г\.?|гор\.?|город)\s*(.+)$", chunk, flags=re.IGNORECASE)
        if match:
            city = _normalize_text(match.group(1))
            if city:
                return city
    skip_pattern = re.compile(
        r"(россия|рф|область|обл\.|край|республика|респ\.|район|р-н|автоном|округ|ул\.|улица|проспект|пр-т|переулок|пер\.|шоссе|наб\.|набережная|бульвар|бул\.|площадь|пл\.|дом|д\.|строение|стр\.|корпус|корп\.|кв\.|офис|оф\.|пом\.|эт\.|мкр\.|микрорайон)",
        flags=re.IGNORECASE,
    )
    for chunk in chunks:
        if skip_pattern.search(chunk):
            continue
        if len(chunk) <= 80:
            return chunk
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


def _company_official_email(company: Client, contact: Contact | None = None) -> str:
    contact = contact or _resolve_contact_for_company(company)
    contact_email = _normalize_text(getattr(contact, "email", ""))
    if contact_email:
        return contact_email
    return _company_email(company)


def _company_phone(company: Client) -> str:
    return _normalize_text(company.phone) or "-"


def _company_signature_label(company: Client) -> str:
    contact = _resolve_contact_for_company(company)
    full_name = _normalize_text(f"{getattr(contact, 'first_name', '')} {getattr(contact, 'last_name', '')}")
    return full_name or "_____________"


def _company_requisites_line(company: Client) -> str:
    return f"{_company_address(company)} / ИНН {_company_inn(company)} / КПП {_company_kpp(company)} / ОГРН {_company_ogrn(company)}"


def _company_bank_requisites_line(company: Client) -> str:
    return f"р/с {_company_account(company)}, {_company_bank(company)}, БИК {_company_bik(company)}, к/с {_company_correspondent_account(company)}"


def _company_contacts_line(company: Client) -> str:
    return f"{_company_email(company)} / {_company_phone(company)}"


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


def _write_docx_from_template(template_path: Path, xml: str) -> bytes:
    with ZipFile(template_path, "r") as source_zip:
        result = BytesIO()
        with ZipFile(result, "w", compression=ZIP_DEFLATED) as target_zip:
            for item in source_zip.infolist():
                data = xml.encode("utf-8") if item.filename == "word/document.xml" else source_zip.read(item.filename)
                target_zip.writestr(item, data)
        return result.getvalue()


def _normalize_generated_payload(contract: SettlementContract, payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    template_code = _template_code(source)
    normalized = {**source, "template_code": template_code}
    normalized["customer_contact_id"] = source.get("customer_contact_id")
    if template_code == OFFER_AGREEMENT_TEMPLATE_CODE:
        acceptance_mode = _normalize_text(source.get("offer_acceptance_mode")) or "days"
        explicit_date = _payload_date(source, "offer_acceptance_deadline_date")
        if acceptance_mode == "date" and explicit_date is None:
            acceptance_mode = "days"
        normalized.update({
            "offer_acceptance_mode": acceptance_mode,
            "offer_acceptance_term_days": _payload_int(source, "offer_acceptance_term_days", DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS),
            "offer_acceptance_deadline_date": explicit_date.isoformat() if explicit_date is not None else "",
            "offer_advance_payment_days": _payload_int(source, "offer_advance_payment_days", DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS),
            "offer_final_payment_days": _payload_int(source, "offer_final_payment_days", DEFAULT_OFFER_FINAL_PAYMENT_DAYS),
            "offer_acceptance_days": _payload_int(source, "offer_acceptance_days", DEFAULT_OFFER_ACCEPTANCE_DAYS),
            "offer_penalty_rate": _serialize_decimal(source.get("offer_penalty_rate"), DEFAULT_OFFER_PENALTY_RATE),
            "offer_penalty_cap_percent": _serialize_decimal(source.get("offer_penalty_cap_percent"), DEFAULT_OFFER_PENALTY_CAP_PERCENT),
        })
    return normalized


def _offer_acceptance_deadline(contract: SettlementContract, payload: dict) -> date:
    contract_date = contract.start_date or timezone.localdate()
    explicit_date = _payload_date(payload, "offer_acceptance_deadline_date")
    if _normalize_text(payload.get("offer_acceptance_mode")) == "date" and explicit_date is not None:
        return explicit_date
    acceptance_days = max(1, _payload_int(payload, "offer_acceptance_term_days", DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS))
    return contract_date + timedelta(days=acceptance_days)


def _build_service_agreement_docx(contract: SettlementContract, executor_company: Client, payload: dict) -> bytes:
    if not SERVICE_AGREEMENT_TEMPLATE_PATH.exists():
        raise ValidationError({"template": "Шаблон договора не найден в проекте."})

    customer_company = contract.client
    contract_date = contract.start_date or timezone.localdate()
    customer_contact = _resolve_contract_contact(customer_company, payload.get("customer_contact_id"))
    customer_position, customer_name = _company_representative(
        customer_company,
        default_position="уполномоченного представителя",
        default_name="_____________",
        contact=customer_contact,
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
    xml = _replace_text(xml, "и [___] лет после его прекращения.", "и 3 лет после его прекращения.", count=1)
    xml = _replace_text(
        xml,
        "электронная почта [указать], система управления проектом [указать], а также иные письменно согласованные каналы связи.",
        f"электронная почта {_company_official_email(customer_company, customer_contact)}, а также иные письменно согласованные каналы связи.",
        count=1,
    )

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
    return _write_docx_from_template(SERVICE_AGREEMENT_TEMPLATE_PATH, xml)


def _build_offer_agreement_docx(contract: SettlementContract, executor_company: Client, payload: dict) -> bytes:
    if not OFFER_AGREEMENT_TEMPLATE_PATH.exists():
        raise ValidationError({"template": "Шаблон оферты не найден в проекте."})

    customer_company = contract.client
    contract_date = contract.start_date or timezone.localdate()
    acceptance_deadline = _offer_acceptance_deadline(contract, payload)
    advance_payment_days = _payload_int(payload, "offer_advance_payment_days", DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS)
    final_payment_days = _payload_int(payload, "offer_final_payment_days", DEFAULT_OFFER_FINAL_PAYMENT_DAYS)
    acceptance_days = _payload_int(payload, "offer_acceptance_days", DEFAULT_OFFER_ACCEPTANCE_DAYS)
    penalty_rate = _payload_decimal(payload, "offer_penalty_rate", DEFAULT_OFFER_PENALTY_RATE)
    penalty_cap_percent = _payload_decimal(payload, "offer_penalty_cap_percent", DEFAULT_OFFER_PENALTY_CAP_PERCENT)
    executor_position, executor_name = _company_representative(
        executor_company,
        default_position="генерального директора",
        default_name="_____________",
    )
    executor_signatory = f"{executor_position} {executor_name}".strip()

    with ZipFile(OFFER_AGREEMENT_TEMPLATE_PATH, "r") as source_zip:
        xml = source_zip.read("word/document.xml").decode("utf-8")

    xml = _replace_text(xml, "[___]", _normalize_text(contract.number) or _next_contract_number(), count=1)
    xml = _replace_text(xml, "[__________]", _company_city(executor_company), count=1)
    xml = _replace_text(xml, "[___] __________ 20__ г.", _format_date_human_plain(contract_date), count=1)
    xml = _replace_text(xml, "[Полное наименование Заказчика]", _company_name(customer_company))
    xml = _replace_text(xml, "[Полное наименование Исполнителя]", _company_offer_executor_display_name(executor_company), count=1)
    xml = _replace_text(
        xml,
        ", ОГРН [__________], ИНН [__________], в лице [ФИО, должность], действующего на основании [Устава / доверенности], именуемое в дальнейшем ",
        f", ОГРН {_company_ogrn(executor_company)}, ИНН {_company_inn(executor_company)}, в лице {executor_signatory}, действующего на основании Устава, именуемое в дальнейшем ",
        count=1,
    )
    xml = _replace_text(
        xml,
        ", ОГРН [__________], ИНН [__________], именуемому в дальнейшем ",
        f", ОГРН {_company_ogrn(customer_company)}, ИНН {_company_inn(customer_company)}, именуемому в дальнейшем ",
        count=1,
    )
    xml = _replace_text(
        xml,
        "2.1. Настоящая оферта адресована Заказчику, указанному в преамбуле, и действует до [___] __________ 20__ г. включительно.",
        f"2.1. Настоящая оферта адресована Заказчику, указанному в преамбуле, и действует до {_format_date_human_plain(acceptance_deadline)} включительно.",
        count=1,
    )
    xml = _replace_text(
        xml,
        "4.2. При выполнении работ по фиксированной стоимости этапа Заказчик оплачивает аванс в размере [___] % стоимости соответствующего этапа (или пилотного проекта) в течение [___] рабочих дней с даты выставления счета, а оставшуюся часть стоимости — в течение [___] рабочих дней с даты подписания акта либо наступления последствий, предусмотренных разделом 5 настоящей оферты.",
        (
            "4.2. При выполнении работ по фиксированной стоимости этапа Заказчик оплачивает аванс "
            f"в размере {_format_decimal(contract.advance_percent or 0)} % стоимости соответствующего этапа (или пилотного проекта) "
            f"в течение {advance_payment_days} рабочих дней с даты выставления счета, а оставшуюся часть стоимости — "
            f"в течение {final_payment_days} рабочих дней с даты подписания акта либо наступления последствий, предусмотренных разделом 5 настоящей оферты."
        ),
        count=1,
    )
    xml = _replace_text(
        xml,
        "4.3. Если применяется почасовая модель, стоимость одного часа работ Исполнителя составляет [__________] рублей.",
        f"4.3. Если применяется почасовая модель, стоимость одного часа работ Исполнителя составляет {_format_decimal(contract.hourly_rate or 0)} рублей.",
        count=1,
    )
    xml = _replace_text(
        xml,
        "5.2. Заказчик обязан в течение [___] рабочих дней с даты получения акта либо подписать акт, либо направить мотивированный письменный отказ с конкретным перечнем недостатков.",
        f"5.2. Заказчик обязан в течение {acceptance_days} рабочих дней с даты получения акта либо подписать акт, либо направить мотивированный письменный отказ с конкретным перечнем недостатков.",
        count=1,
    )
    xml = _replace_text(
        xml,
        "10.2. В случае просрочки оплаты Заказчик уплачивает Исполнителю неустойку в размере [___] % от суммы просроченного платежа за каждый день просрочки, но не более [___] % от суммы соответствующей задолженности.",
        (
            "10.2. В случае просрочки оплаты Заказчик уплачивает Исполнителю неустойку "
            f"в размере {_format_decimal(penalty_rate)} % от суммы просроченного платежа за каждый день просрочки, "
            f"но не более {_format_decimal(penalty_cap_percent)} % от суммы соответствующей задолженности."
        ),
        count=1,
    )
    xml = _replace_text(
        xml,
        "11.2. Каждая из Сторон вправе отказаться от исполнения договора в части неисполненных обязательств, письменно уведомив другую Сторону не менее чем за [___] календарных дней.",
        f"11.2. Каждая из Сторон вправе отказаться от исполнения договора в части неисполненных обязательств, письменно уведомив другую Сторону не менее чем за {int(contract.termination_notice_days or DEFAULT_TERMINATION_NOTICE_DAYS)} календарных дней.",
        count=1,
    )
    xml = _replace_text(
        xml,
        "12.2. Срок ответа на претензию составляет [___] календарных дней с даты ее получения.",
        f"12.2. Срок ответа на претензию составляет {int(contract.claim_response_days or DEFAULT_CLAIM_RESPONSE_DAYS)} календарных дней с даты ее получения.",
        count=1,
    )

    xml = _replace_text(xml, "[____________________]", _company_name(executor_company), count=1)
    xml = _replace_text(xml, "[____________________]", _company_requisites_line(executor_company), count=1)
    xml = _replace_text(xml, "[р/с, банк, БИК, к/с]", _company_bank_requisites_line(executor_company), count=1)
    xml = _replace_text(xml, "[____________________]", _company_contacts_line(executor_company), count=1)
    xml = _replace_text(xml, "[ФИО, должность]", executor_signatory, count=1)
    return _write_docx_from_template(OFFER_AGREEMENT_TEMPLATE_PATH, xml)


def _build_generated_contract_docx(contract: SettlementContract, executor_company: Client, payload: dict) -> bytes:
    template_code = _template_code(payload)
    if template_code == OFFER_AGREEMENT_TEMPLATE_CODE:
        return _build_offer_agreement_docx(contract, executor_company, payload)
    return _build_service_agreement_docx(contract, executor_company, payload)


def _save_generated_contract_file(contract: SettlementContract, payload: dict) -> SettlementContract:
    template_code = _template_code(payload)
    executor_company = _select_executor_company(payload.get("executor_company_id"))
    normalized_payload = _normalize_generated_payload(contract, {
        **payload,
        "template_code": template_code,
        "executor_company_id": executor_company.pk,
    })
    document_bytes = _build_generated_contract_docx(contract, executor_company, normalized_payload)
    filename = _contract_display_name(contract)
    contract.original_name = filename
    contract.generator_payload = {
        **normalized_payload,
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
        "end_date",
        "note",
        "generator_payload",
        "original_name",
        "file",
        "updated_at",
    ])
    return contract


@transaction.atomic
def generate_service_agreement_contract(
    *,
    client: Client,
    representative_contact: Contact | None = None,
    advance_percent: Decimal | int | float | str,
    hourly_rate: Decimal | int | float | str,
    warranty_days: int = DEFAULT_WARRANTY_DAYS,
    claim_response_days: int = DEFAULT_CLAIM_RESPONSE_DAYS,
    termination_notice_days: int = DEFAULT_TERMINATION_NOTICE_DAYS,
) -> SettlementContract:
    if representative_contact is not None and representative_contact.client_id != client.pk:
        raise ValidationError({"representative_contact": "Контакт должен принадлежать выбранной компании."})
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
            "customer_contact_id": representative_contact.pk if representative_contact is not None else None,
        },
    )
    return refresh_generated_contract(contract)


@transaction.atomic
def generate_offer_agreement_contract(
    *,
    client: Client,
    representative_contact: Contact | None = None,
    advance_percent: Decimal | int | float | str,
    hourly_rate: Decimal | int | float | str,
    claim_response_days: int = DEFAULT_CLAIM_RESPONSE_DAYS,
    termination_notice_days: int = DEFAULT_TERMINATION_NOTICE_DAYS,
    offer_acceptance_term_days: int = DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS,
    offer_acceptance_deadline_date: date | None = None,
    offer_advance_payment_days: int = DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS,
    offer_final_payment_days: int = DEFAULT_OFFER_FINAL_PAYMENT_DAYS,
    offer_acceptance_days: int = DEFAULT_OFFER_ACCEPTANCE_DAYS,
    offer_penalty_rate: Decimal | int | float | str = DEFAULT_OFFER_PENALTY_RATE,
    offer_penalty_cap_percent: Decimal | int | float | str = DEFAULT_OFFER_PENALTY_CAP_PERCENT,
) -> SettlementContract:
    if representative_contact is not None and representative_contact.client_id != client.pk:
        raise ValidationError({"representative_contact": "Контакт должен принадлежать выбранной компании."})
    executor_company = _select_executor_company()
    acceptance_mode = "date" if offer_acceptance_deadline_date is not None else "days"
    contract = SettlementContract.objects.create(
        client=client,
        title=DEFAULT_OFFER_CONTRACT_TITLE,
        number=_next_contract_number(),
        currency=_normalize_text(client.currency).upper() or "RUB",
        advance_percent=Decimal(advance_percent or 0).quantize(Decimal("0.01")),
        hourly_rate=Decimal(hourly_rate or 0).quantize(Decimal("0.01")),
        warranty_days=DEFAULT_WARRANTY_DAYS,
        claim_response_days=int(claim_response_days or DEFAULT_CLAIM_RESPONSE_DAYS),
        termination_notice_days=int(termination_notice_days or DEFAULT_TERMINATION_NOTICE_DAYS),
        start_date=timezone.localdate(),
        generator_payload={
            "template_code": OFFER_AGREEMENT_TEMPLATE_CODE,
            "executor_company_id": executor_company.pk,
            "customer_contact_id": representative_contact.pk if representative_contact is not None else None,
            "offer_acceptance_mode": acceptance_mode,
            "offer_acceptance_term_days": int(offer_acceptance_term_days or DEFAULT_OFFER_ACCEPTANCE_TERM_DAYS),
            "offer_acceptance_deadline_date": offer_acceptance_deadline_date.isoformat() if offer_acceptance_deadline_date is not None else "",
            "offer_advance_payment_days": int(offer_advance_payment_days or DEFAULT_OFFER_ADVANCE_PAYMENT_DAYS),
            "offer_final_payment_days": int(offer_final_payment_days or DEFAULT_OFFER_FINAL_PAYMENT_DAYS),
            "offer_acceptance_days": int(offer_acceptance_days or DEFAULT_OFFER_ACCEPTANCE_DAYS),
            "offer_penalty_rate": _serialize_decimal(offer_penalty_rate, DEFAULT_OFFER_PENALTY_RATE),
            "offer_penalty_cap_percent": _serialize_decimal(offer_penalty_cap_percent, DEFAULT_OFFER_PENALTY_CAP_PERCENT),
        },
    )
    return refresh_generated_contract(contract)


@transaction.atomic
def generate_contract(*, template_code: str, **kwargs) -> SettlementContract:
    if template_code == OFFER_AGREEMENT_TEMPLATE_CODE:
        kwargs.pop("warranty_days", None)
        return generate_offer_agreement_contract(**kwargs)
    kwargs.pop("offer_acceptance_term_days", None)
    kwargs.pop("offer_acceptance_deadline_date", None)
    kwargs.pop("offer_advance_payment_days", None)
    kwargs.pop("offer_final_payment_days", None)
    kwargs.pop("offer_acceptance_days", None)
    kwargs.pop("offer_penalty_rate", None)
    kwargs.pop("offer_penalty_cap_percent", None)
    return generate_service_agreement_contract(**kwargs)


def refresh_generated_contract(contract: SettlementContract) -> SettlementContract:
    payload = contract.generator_payload if isinstance(contract.generator_payload, dict) else {}
    if _template_code(payload) not in GENERATED_CONTRACT_TEMPLATE_CODES:
        payload = {**payload, "template_code": SERVICE_AGREEMENT_TEMPLATE_CODE}
    if not _normalize_text(contract.title):
        contract.title = _default_contract_title(_template_code(payload))
    return _save_generated_contract_file(contract, payload)


def refresh_generated_service_agreement(contract: SettlementContract) -> SettlementContract:
    payload = contract.generator_payload if isinstance(contract.generator_payload, dict) else {}
    contract.generator_payload = {**payload, "template_code": SERVICE_AGREEMENT_TEMPLATE_CODE}
    if not _normalize_text(contract.title):
        contract.title = DEFAULT_CONTRACT_TITLE
    return refresh_generated_contract(contract)
