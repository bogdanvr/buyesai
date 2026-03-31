from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from crm.models import Client, Deal, DealDocument, SettlementContract, SettlementDocument


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

RUSSIAN_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]
RUSSIAN_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
RUSSIAN_TEENS = [
    "десять",
    "одиннадцать",
    "двенадцать",
    "тринадцать",
    "четырнадцать",
    "пятнадцать",
    "шестнадцать",
    "семнадцать",
    "восемнадцать",
    "девятнадцать",
]
RUSSIAN_UNITS_MALE = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
RUSSIAN_UNITS_FEMALE = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]

CURRENCY_WORD_FORMS = {
    "RUB": (("рубль", "рубля", "рублей"), ("копейка", "копейки", "копеек")),
    "KZT": (("тенге", "тенге", "тенге"), ("тиын", "тиына", "тиынов")),
    "USD": (("доллар", "доллара", "долларов"), ("цент", "цента", "центов")),
    "EUR": (("евро", "евро", "евро"), ("цент", "цента", "центов")),
}

PAGE_MARGIN_TOP = "1134"
PAGE_MARGIN_SIDE = "1134"
PAGE_MARGIN_BOTTOM = "1134"
PAGE_HEADER_MARGIN = "708"
PAGE_FOOTER_MARGIN = "708"
AUTO_CONTRACT = object()


@dataclass(frozen=True)
class ActLineItem:
    description: str
    quantity: Decimal
    unit: str
    price: Decimal

    @property
    def total(self) -> Decimal:
        return _quantize_money(self.quantity * self.price)


def _format_date_human(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return f"{value.day} {RUSSIAN_MONTHS.get(value.month, '')} {value.year} г."


def _format_date_short(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return value.strftime("%d.%m.%Y")


def _format_amount(value: Decimal | int | float | str) -> str:
    amount = _quantize_money(value)
    formatted = f"{amount:,.2f}"
    return formatted.replace(",", " ").replace(".", ",")


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _quantize_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _format_compact_number(value: Decimal | int | float | str) -> str:
    normalized_value = Decimal(value or 0)
    text = format(normalized_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _pluralize(number: int, forms: tuple[str, str, str]) -> str:
    value = abs(int(number)) % 100
    if 10 < value < 20:
        return forms[2]
    value = value % 10
    if value == 1:
        return forms[0]
    if 1 < value < 5:
        return forms[1]
    return forms[2]


def _triad_to_words(number: int, female: bool = False) -> str:
    if number <= 0:
        return ""
    hundreds = number // 100
    tens_units = number % 100
    tens = tens_units // 10
    units = tens_units % 10
    parts = []
    if hundreds:
        parts.append(RUSSIAN_HUNDREDS[hundreds])
    if 10 <= tens_units <= 19:
        parts.append(RUSSIAN_TEENS[tens_units - 10])
    else:
        if tens:
            parts.append(RUSSIAN_TENS[tens])
        if units:
            parts.append((RUSSIAN_UNITS_FEMALE if female else RUSSIAN_UNITS_MALE)[units])
    return " ".join(part for part in parts if part)


def _number_to_russian_words(number: int) -> str:
    if number == 0:
        return "ноль"

    scales = [
        (("миллиард", "миллиарда", "миллиардов"), False),
        (("миллион", "миллиона", "миллионов"), False),
        (("тысяча", "тысячи", "тысяч"), True),
    ]

    parts = []
    billions = number // 1_000_000_000
    millions = (number // 1_000_000) % 1000
    thousands = (number // 1000) % 1000
    remainder = number % 1000
    chunks = [billions, millions, thousands]

    for chunk, (forms, female) in zip(chunks, scales):
        if not chunk:
            continue
        parts.append(_triad_to_words(chunk, female=female))
        parts.append(_pluralize(chunk, forms))

    if remainder:
        parts.append(_triad_to_words(remainder))

    return " ".join(part for part in parts if part)


def _amount_in_words(value: Decimal | int | float | str, currency: str) -> str:
    amount = _quantize_money(value)
    currency_code = _normalize_text(currency).upper() or "RUB"
    major_forms, minor_forms = CURRENCY_WORD_FORMS.get(currency_code, CURRENCY_WORD_FORMS["RUB"])
    major = int(amount)
    minor = int((amount - Decimal(major)) * 100)
    major_words = _number_to_russian_words(major)
    phrase = f"{major_words} {_pluralize(major, major_forms)} {minor:02d} {_pluralize(minor, minor_forms)}"
    return phrase[:1].upper() + phrase[1:]


def _build_party_details(name: str, requisites_parts: list[str]) -> str:
    normalized_parts = [part for part in (part.strip() for part in requisites_parts) if part]
    if not normalized_parts:
        return name
    return f"{name}, {', '.join(normalized_parts)}"


def _company_name(company: Client, fallback_name: str) -> str:
    return _normalize_text(company.legal_name) or _normalize_text(company.name) or fallback_name


def _company_details(company: Client, fallback_name: str) -> tuple[str, str]:
    company_name = _company_name(company, fallback_name)
    account_value = _normalize_text(company.settlement_account or company.iban)
    account_label = "р/с" if _normalize_text(company.currency).upper() == "RUB" else "IBAN"
    requisites_parts = [
        f"ИНН {company.inn}" if company.inn else "",
        f"КПП {company.kpp}" if company.kpp else "",
        f"ОГРН {company.ogrn}" if company.ogrn else "",
        company.address or company.actual_address or "",
        f"{account_label} {account_value}" if account_value else "",
        f"БИК {company.bik}" if company.bik else "",
        f"к/с {company.correspondent_account}" if company.correspondent_account else "",
        company.bank_name or "",
        company.bank_details or "",
    ]
    return company_name, _build_party_details(company_name, requisites_parts)


def _executor_details(executor_company: Client) -> tuple[str, str]:
    if executor_company.company_type != Client.CompanyType.OWN:
        raise ValidationError({"executor_company": "Выберите собственную организацию."})
    return _company_details(executor_company, f"Исполнитель #{executor_company.pk}")


def _customer_details(deal: Deal) -> tuple[str, str]:
    client = deal.client
    if client is None:
        raise ValidationError({"deal": "Для генерации акта у сделки должна быть выбрана компания."})
    return _company_details(client, f"Компания #{client.pk}")


def _paragraph(text: str = "", *, bold: bool = False, align: str = "left", size: int = 24, spacing_after: int = 120) -> str:
    align_xml = ""
    if align == "center":
        align_xml = '<w:jc w:val="center"/>'
    elif align == "right":
        align_xml = '<w:jc w:val="right"/>'

    run_props = [
        '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>',
        f'<w:sz w:val="{size}"/>',
        f'<w:szCs w:val="{size}"/>',
    ]
    if bold:
        run_props.append("<w:b/>")

    lines = str(text or "").split("\n")
    run_chunks = []
    for index, line in enumerate(lines):
        if index:
            run_chunks.append("<w:br/>")
        run_chunks.append(f"<w:t>{escape(line)}</w:t>")
    if not run_chunks:
        run_chunks.append("<w:t></w:t>")

    return (
        "<w:p>"
        f'<w:pPr>{align_xml}<w:spacing w:after="{spacing_after}"/></w:pPr>'
        f"<w:r><w:rPr>{''.join(run_props)}</w:rPr>{''.join(run_chunks)}</w:r>"
        "</w:p>"
    )


def _table_cell(text: str, *, width: int, bold: bool = False, align: str = "left", shaded: bool = False) -> str:
    shading_xml = '<w:shd w:val="clear" w:color="auto" w:fill="D9E7F5"/>' if shaded else ""
    margins_xml = (
        "<w:tcMar>"
        '<w:top w:w="40" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/>'
        '<w:left w:w="40" w:type="dxa"/>'
        '<w:right w:w="40" w:type="dxa"/>'
        "</w:tcMar>"
    )
    return (
        "<w:tc>"
        f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{margins_xml}<w:vAlign w:val="center"/>{shading_xml}</w:tcPr>'
        f"{_paragraph(text, bold=bold, align=align, size=22, spacing_after=0)}"
        "</w:tc>"
    )


def _table_cell_custom(
    text: str,
    *,
    width: int,
    bold: bool = False,
    align: str = "left",
    size: int = 22,
    shaded: bool = False,
    grid_span: int | None = None,
    spacing_after: int = 0,
) -> str:
    shading_xml = '<w:shd w:val="clear" w:color="auto" w:fill="D9E7F5"/>' if shaded else ""
    grid_span_xml = f'<w:gridSpan w:val="{int(grid_span)}"/>' if grid_span and int(grid_span) > 1 else ""
    margins_xml = (
        "<w:tcMar>"
        '<w:top w:w="40" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/>'
        '<w:left w:w="40" w:type="dxa"/>'
        '<w:right w:w="40" w:type="dxa"/>'
        "</w:tcMar>"
    )
    return (
        "<w:tc>"
        f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{grid_span_xml}{margins_xml}<w:vAlign w:val="center"/>{shading_xml}</w:tcPr>'
        f"{_paragraph(text, bold=bold, align=align, size=size, spacing_after=spacing_after)}"
        "</w:tc>"
    )


def _service_table(items: list[ActLineItem]) -> str:
    widths = [500, 4500, 900, 700, 1300, 1500]
    table_width = sum(widths)
    headers = ["№", "Наименование работ, услуг", "Кол-во", "Ед.", "Цена", "Сумма"]
    header_xml = "".join(
        _table_cell(text, width=width, bold=True, align="center", shaded=True)
        for text, width in zip(headers, widths)
    )
    rows_xml = "".join(
        (
            "<w:tr>"
            f"{_table_cell(str(index), width=widths[0], align='center')}"
            f"{_table_cell(item.description, width=widths[1])}"
            f"{_table_cell(_format_compact_number(item.quantity), width=widths[2], align='center')}"
            f"{_table_cell(item.unit or 'час', width=widths[3], align='center')}"
            f"{_table_cell(_format_amount(item.price), width=widths[4], align='right')}"
            f"{_table_cell(_format_amount(item.total), width=widths[5], align='right')}"
            "</w:tr>"
        )
        for index, item in enumerate(items, start=1)
    )
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:left w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:right w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="666666"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="666666"/>'
        "</w:tblBorders>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"{table_width}\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"<w:tr>{header_xml}</w:tr>"
        f"{rows_xml}"
        "</w:tbl>"
    )


def _invoice_payment_table(executor_company: Client) -> str:
    widths = [3600, 1600, 900, 2800]
    table_width = sum(widths)
    bank_name = _normalize_text(executor_company.bank_name) or "Банк не указан"
    bik = _normalize_text(executor_company.bik) or "-"
    correspondent_account = _normalize_text(executor_company.correspondent_account) or "-"
    settlement_account = _normalize_text(executor_company.settlement_account or executor_company.iban) or "-"
    settlement_label = "р/с №"
    inn = _normalize_text(executor_company.inn) or "-"
    kpp = _normalize_text(executor_company.kpp) or "-"
    recipient_name = _company_name(executor_company, "Получатель")
    rows_xml = "".join([
        "<w:tr>"
        f"{_table_cell_custom(bank_name, width=widths[0] + widths[1], bold=True, size=22, grid_span=2)}"
        f"{_table_cell_custom('БИК', width=widths[2], bold=True, size=20)}"
        f"{_table_cell_custom(bik, width=widths[3], size=22)}"
        "</w:tr>",
        "<w:tr>"
        f"{_table_cell_custom('Банк получателя', width=widths[0] + widths[1], size=18, grid_span=2)}"
        f"{_table_cell_custom('к/с №', width=widths[2], bold=True, size=20)}"
        f"{_table_cell_custom(correspondent_account, width=widths[3], size=22)}"
        "</w:tr>",
        "<w:tr>"
        f"{_table_cell_custom(f'ИНН {inn}', width=widths[0], bold=True, size=20)}"
        f"{_table_cell_custom(f'КПП {kpp}', width=widths[1], bold=True, size=20)}"
        f"{_table_cell_custom(settlement_label, width=widths[2], bold=True, size=20)}"
        f"{_table_cell_custom(settlement_account, width=widths[3], size=22)}"
        "</w:tr>",
        "<w:tr>"
        f"{_table_cell_custom(recipient_name, width=widths[0] + widths[1], size=22, grid_span=2)}"
        f"{_table_cell_custom('', width=widths[2], size=20)}"
        f"{_table_cell_custom('', width=widths[3], size=20)}"
        "</w:tr>",
        "<w:tr>"
        f"{_table_cell_custom('Получатель', width=widths[0] + widths[1], size=18, grid_span=2)}"
        f"{_table_cell_custom('', width=widths[2], size=20)}"
        f"{_table_cell_custom('', width=widths[3], size=20)}"
        "</w:tr>",
    ])
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:left w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:bottom w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:right w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:insideH w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:insideV w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        "</w:tblBorders>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"{table_width}\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/><w:jc w:val=\"right\"/>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"{rows_xml}"
        "</w:tbl>"
    )


def _invoice_items_table(items: list[ActLineItem]) -> str:
    widths = [500, 4600, 900, 700, 1200, 1500]
    table_width = sum(widths)
    headers = ["№", "Товары (работы, услуги)", "Кол-во", "Ед.", "Цена", "Сумма"]
    header_xml = "".join(
        _table_cell_custom(text, width=width, bold=True, align="center", size=22, shaded=True)
        for text, width in zip(headers, widths)
    )
    rows_xml = "".join(
        (
            "<w:tr>"
            f"{_table_cell_custom(str(index), width=widths[0], align='center', size=20)}"
            f"{_table_cell_custom(item.description, width=widths[1], size=20)}"
            f"{_table_cell_custom(_format_compact_number(item.quantity), width=widths[2], align='right', size=20)}"
            f"{_table_cell_custom(item.unit or 'шт.', width=widths[3], align='center', size=20)}"
            f"{_table_cell_custom(_format_amount(item.price), width=widths[4], align='right', size=20)}"
            f"{_table_cell_custom(_format_amount(item.total), width=widths[5], align='right', size=20)}"
            "</w:tr>"
        )
        for index, item in enumerate(items, start=1)
    )
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:left w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:bottom w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:right w:val="single" w:sz="10" w:space="0" w:color="222222"/>'
        '<w:insideH w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:insideV w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        "</w:tblBorders>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"{table_width}\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"<w:tr>{header_xml}</w:tr>"
        f"{rows_xml}"
        "</w:tbl>"
    )


def _invoice_totals_table(amount: Decimal, currency: str) -> str:
    widths = [2200, 1800]
    table_width = sum(widths)
    rows = [
        ("Итого:", _format_amount(amount)),
        ("Без налога (НДС)", "-"),
        ("Всего к оплате:", f"{_format_amount(amount)} {currency}"),
    ]
    row_xml = "".join(
        "<w:tr>"
        f"{_table_cell_custom(label, width=widths[0], bold=True, align='right', size=22)}"
        f"{_table_cell_custom(value, width=widths[1], bold=True, align='right', size=22)}"
        "</w:tr>"
        for label, value in rows
    )
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
        '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
        "</w:tblBorders>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"{table_width}\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/>{borders_xml}<w:jc w:val=\"right\"/></w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"{row_xml}"
        "</w:tbl>"
    )


def _invoice_footer_signatures() -> str:
    widths = [2500, 2800, 1700, 2200]
    table_width = sum(widths)
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
        '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
        "</w:tblBorders>"
    )
    row1 = (
        "<w:tr>"
        f"{_table_cell_custom('Руководитель', width=widths[0], bold=True, size=22)}"
        f"{_table_cell_custom('________________________', width=widths[1], size=22)}"
        f"{_table_cell_custom('Бухгалтер', width=widths[2], bold=True, size=22)}"
        f"{_table_cell_custom('________________________', width=widths[3], size=22)}"
        "</w:tr>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"{table_width}\" w:type=\"dxa\"/><w:tblLayout w:type=\"fixed\"/><w:jc w:val=\"right\"/>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"{row1}"
        "</w:tbl>"
    )
    rows_xml = "".join(
        (
            "<w:tr>"
            f"{_table_cell(str(index), width=widths[0], align='center')}"
            f"{_table_cell(item.description, width=widths[1])}"
            f"{_table_cell(_format_compact_number(item.quantity), width=widths[2], align='center')}"
            f"{_table_cell(item.unit or 'час', width=widths[3], align='center')}"
            f"{_table_cell(_format_amount(item.price), width=widths[4], align='right')}"
            f"{_table_cell(_format_amount(item.total), width=widths[5], align='right')}"
            "</w:tr>"
        )
        for index, item in enumerate(items, start=1)
    )
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:left w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:right w:val="single" w:sz="8" w:space="0" w:color="222222"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="666666"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="666666"/>'
        "</w:tblBorders>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"<w:tr>{header_xml}</w:tr>"
        f"{rows_xml}"
        "</w:tbl>"
    )


def _signatures_table(executor_name: str, customer_name: str) -> str:
    widths = [4600, 4600]
    grid_xml = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders_xml = (
        "<w:tblBorders>"
        '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
        '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
        "</w:tblBorders>"
    )
    left_cell = (
        "<w:tc><w:tcPr><w:tcW w:w=\"4600\" w:type=\"dxa\"/></w:tcPr>"
        f"{_paragraph('ИСПОЛНИТЕЛЬ', bold=True, size=24, spacing_after=40)}"
        f"{_paragraph(executor_name, size=22, spacing_after=240)}"
        f"{_paragraph('_______________________________', size=22, spacing_after=0)}"
        "</w:tc>"
    )
    right_cell = (
        "<w:tc><w:tcPr><w:tcW w:w=\"4600\" w:type=\"dxa\"/></w:tcPr>"
        f"{_paragraph('ЗАКАЗЧИК', bold=True, size=24, spacing_after=40)}"
        f"{_paragraph(customer_name, size=22, spacing_after=240)}"
        f"{_paragraph('_______________________________', size=22, spacing_after=0)}"
        "</w:tc>"
    )
    return (
        "<w:tbl>"
        f"<w:tblPr>{borders_xml}</w:tblPr>"
        f"<w:tblGrid>{grid_xml}</w:tblGrid>"
        f"<w:tr>{left_cell}{right_cell}</w:tr>"
        "</w:tbl>"
    )


def _document_xml(*, title: str, executor_line: str, customer_line: str, basis_line: str, items: list[ActLineItem], amount: Decimal, currency: str) -> str:
    return _service_document_xml(
        title=title,
        executor_line=executor_line,
        customer_line=customer_line,
        basis_line=basis_line,
        items=items,
        amount=amount,
        currency=currency,
        summary_line=f"Всего оказано услуг на сумму {_format_amount(amount)} {currency}.",
        footer_text="Вышеперечисленные услуги выполнены полностью и в срок. Заказчик претензий по объему, качеству и срокам оказания услуг не имеет.",
        include_signatures=True,
    )


def _service_document_xml(
    *,
    title: str,
    executor_line: str,
    customer_line: str,
    basis_line: str,
    items: list[ActLineItem],
    amount: Decimal,
    currency: str,
    summary_line: str,
    footer_text: str,
    include_signatures: bool,
) -> str:
    amount_text = _format_amount(amount)
    body = [
        _paragraph(title, bold=True, align="center", size=30, spacing_after=200),
        _paragraph(f"Исполнитель: {executor_line}", size=22),
        _paragraph(f"Заказчик: {customer_line}", size=22),
        _paragraph(f"Основание: {basis_line}", size=22, spacing_after=180),
        _service_table(items),
        _paragraph("", spacing_after=80),
        _paragraph(f"Итого: {amount_text} {currency}", bold=True, align="right", size=24, spacing_after=160),
        _paragraph(summary_line, size=22),
        _paragraph(footer_text, size=22, spacing_after=260),
        _signatures_table(executor_line.split(',')[0], customer_line.split(',')[0]) if include_signatures else "",
        (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="{PAGE_MARGIN_TOP}" w:right="{PAGE_MARGIN_SIDE}" w:bottom="{PAGE_MARGIN_BOTTOM}" '
            f'w:left="{PAGE_MARGIN_SIDE}" w:header="{PAGE_HEADER_MARGIN}" w:footer="{PAGE_FOOTER_MARGIN}" w:gutter="0"/>'
            "</w:sectPr>"
        ),
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}</w:body>"
        "</w:document>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults>'
        '<w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="120"/></w:pPr></w:pPrDefault>'
        "</w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
        "</w:styles>"
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _document_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _core_properties_xml() -> str:
    return _document_core_properties_xml("Акт об оказании услуг")


def _document_core_properties_xml(title: str) -> str:
    now_iso = timezone.now().replace(microsecond=0).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(title)}</dc:title>"
        "<dc:creator>CRM</dc:creator>"
        "<cp:lastModifiedBy>CRM</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now_iso}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now_iso}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_properties_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>CRM</Application>"
        "</Properties>"
    )


def _coerce_line_item(raw_item: ActLineItem | dict) -> ActLineItem:
    if isinstance(raw_item, ActLineItem):
        return raw_item
    description = _normalize_text(raw_item.get("description"))
    unit = _normalize_text(raw_item.get("unit")) or "час"
    quantity = _quantize_money(raw_item.get("quantity"))
    price = _quantize_money(raw_item.get("price"))
    if not description:
        raise ValidationError({"items": "Заполните наименование услуги."})
    if quantity <= 0 or price <= 0:
        raise ValidationError({"items": "Количество и стоимость должны быть больше нуля."})
    return ActLineItem(description=description, quantity=quantity, unit=unit, price=price)


def _line_items_payload(items: list[ActLineItem]) -> list[dict[str, str]]:
    return [
        {
            "description": item.description,
            "quantity": format(item.quantity, "f"),
            "unit": item.unit,
            "price": format(item.price, "f"),
        }
        for item in items
    ]


def _generator_payload(*, executor_company: Client, items: list[ActLineItem], contract: SettlementContract | None = None) -> dict:
    return {
        "executor_company_id": executor_company.pk,
        "contract_id": getattr(contract, "pk", None),
        "items": _line_items_payload(items),
    }


def _document_file_name(*, file_prefix: str, settlement_document: SettlementDocument) -> str:
    return f"{file_prefix}-{settlement_document.number or settlement_document.pk}.docx"


def _document_original_name(*, original_label: str, settlement_document: SettlementDocument) -> str:
    return f"{original_label} № {settlement_document.number} от {_format_date_short(settlement_document.document_date)}.docx"


def _append_generated_document_update_event(*, deal: Deal | None, deal_document: DealDocument, settlement_document: SettlementDocument, actor) -> None:
    if deal is None or not getattr(deal, "pk", None):
        return
    happened_at = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M")
    document_name = _normalize_text(deal_document.original_name) or f"Документ #{deal_document.pk}"
    actor_name = ""
    if actor is not None:
        actor_name = _normalize_text(actor.get_full_name() if hasattr(actor, "get_full_name") else "") or _normalize_text(getattr(actor, "username", ""))
    document_type = _normalize_text(getattr(settlement_document, "document_type", ""))
    if document_type == SettlementDocument.DocumentType.INVOICE:
        result_text = f"Редактирование счета: {document_name}"
    elif document_type == SettlementDocument.DocumentType.REALIZATION:
        result_text = f"Редактирование акта: {document_name}"
    else:
        result_text = f"Редактирование документа: {document_name}"
    entry = "\n".join(
        [
            happened_at,
            f"Результат: {result_text}",
            "event_type: document_edited",
            "priority: medium",
            "title: Документ сделки",
            f"actor_name: {actor_name}",
            f"document_name: {document_name}",
            f"document_url: {reverse('deal-documents-download', kwargs={'pk': deal_document.pk})}",
            "document_scope: deal",
            f"settlement_document_id: {settlement_document.pk}",
            f"settlement_document_type: {document_type}",
        ]
    )
    current_events = _normalize_text(getattr(deal, "events", ""))
    updated_events = entry if not current_events else f"{entry}\n\n{current_events}"
    Deal.objects.filter(pk=deal.pk).update(events=updated_events)


def _document_type_from_original_name(original_name: str) -> str:
    normalized_name = _normalize_text(original_name).lower().replace("ё", "е")
    if "счет" in normalized_name:
        return SettlementDocument.DocumentType.INVOICE
    if "акт" in normalized_name:
        return SettlementDocument.DocumentType.REALIZATION
    return ""


def _document_number_from_original_name(original_name: str) -> str:
    match = re.search(r"№\s*([A-Za-zА-Яа-я0-9\-\/]+)", _normalize_text(original_name))
    return _normalize_text(match.group(1) if match else "")


def resolve_settlement_document_for_deal_document(deal_document: DealDocument) -> SettlementDocument | None:
    linked = getattr(deal_document, "settlement_document", None)
    if linked is not None:
        return linked
    deal_id = getattr(deal_document, "deal_id", None)
    if not deal_id:
        return None
    document_type = _document_type_from_original_name(getattr(deal_document, "original_name", ""))
    document_number = _document_number_from_original_name(getattr(deal_document, "original_name", ""))
    if not document_type or not document_number:
        return None
    return SettlementDocument.objects.filter(
        deal_id=deal_id,
        document_type=document_type,
        number=document_number,
    ).order_by("-id").first()


def deal_document_generator_context(deal_document: DealDocument) -> dict:
    settlement_document = resolve_settlement_document_for_deal_document(deal_document)
    if settlement_document is None:
        return {
            "editable": False,
            "document_type": "",
            "settlement_document_id": None,
            "generator_payload": {},
        }
    payload = getattr(settlement_document, "generator_payload", None) or {}
    normalized_payload = payload if isinstance(payload, dict) else {}
    items = normalized_payload.get("items") if isinstance(normalized_payload.get("items"), list) else []
    if not items:
        items = [
            {
                "description": _normalize_text(getattr(deal_document.deal, "title", "")) or _normalize_text(getattr(settlement_document, "title", "")) or "Услуга",
                "quantity": "1.00",
                "unit": "час",
                "price": format(Decimal(getattr(settlement_document, "amount", 0) or 0).quantize(Decimal("0.01")), "f"),
            }
        ]
    return {
        "editable": settlement_document.document_type in {
            SettlementDocument.DocumentType.INVOICE,
            SettlementDocument.DocumentType.REALIZATION,
        },
        "document_type": settlement_document.document_type,
        "settlement_document_id": settlement_document.pk,
        "generator_payload": {
            "executor_company_id": normalized_payload.get("executor_company_id"),
            "contract_id": normalized_payload.get("contract_id", settlement_document.contract_id),
            "items": items,
            "number": settlement_document.number,
            "document_date": _format_date_short(settlement_document.document_date),
        },
    }


def build_act_docx_bytes(*, settlement_document: SettlementDocument, deal: Deal, executor_company: Client, items: list[ActLineItem | dict]) -> bytes:
    executor_name, executor_requisites = _executor_details(executor_company)
    customer_name, customer_line = _customer_details(deal)
    contract = getattr(settlement_document, "contract", None)
    basis_line = _normalize_text(getattr(contract, "number", "")) or _normalize_text(getattr(contract, "title", ""))
    if basis_line:
        basis_line = f"Договор {basis_line}"
    else:
        basis_line = f"Сделка «{_normalize_text(deal.title) or f'#{deal.pk}'}»"

    title = f"Акт об оказании услуг № {settlement_document.number} от {_format_date_human(settlement_document.document_date)}"
    line_items = [_coerce_line_item(item) for item in items]
    amount = Decimal(settlement_document.amount or 0)
    currency = _normalize_text(settlement_document.currency) or "RUB"
    document_xml = _document_xml(
        title=title,
        executor_line=executor_requisites,
        customer_line=customer_line,
        basis_line=basis_line,
        items=line_items,
        amount=amount,
        currency=currency,
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("docProps/core.xml", _document_core_properties_xml("Акт об оказании услуг"))
        archive.writestr("docProps/app.xml", _app_properties_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _styles_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_relationships_xml())
    return output.getvalue()


def build_invoice_docx_bytes(*, settlement_document: SettlementDocument, deal: Deal, executor_company: Client, items: list[ActLineItem | dict]) -> bytes:
    _, executor_requisites = _executor_details(executor_company)
    _, customer_line = _customer_details(deal)
    contract = getattr(settlement_document, "contract", None)
    basis_line = _normalize_text(getattr(contract, "number", "")) or _normalize_text(getattr(contract, "title", ""))
    if basis_line:
        basis_line = f"Договор {basis_line}"
    else:
        basis_line = f"Сделка «{_normalize_text(deal.title) or f'#{deal.pk}'}»"

    title = f"Счет на оплату № {settlement_document.number} от {_format_date_human(settlement_document.document_date)}"
    line_items = [_coerce_line_item(item) for item in items]
    amount = Decimal(settlement_document.amount or 0)
    currency = _normalize_text(settlement_document.currency) or "RUB"
    amount_in_words = _amount_in_words(amount, currency)
    footer_lines = [
        f"Всего наименований {len(line_items)}, на сумму {_format_amount(amount)} {currency}.",
        amount_in_words,
    ]
    if settlement_document.due_date:
        footer_lines.append(f"Оплатить не позднее {_format_date_short(settlement_document.due_date)}")
    footer_lines.extend([
        "Оплата данного счета означает согласие с условиями поставки товара или оказания услуг.",
        "Уведомление об оплате желательно направить поставщику.",
    ])
    body = [
        _invoice_payment_table(executor_company),
        _paragraph("", spacing_after=90),
        _paragraph(title, bold=True, align="left", size=34, spacing_after=180),
        _paragraph(f"Поставщик\n(Исполнитель): {executor_requisites}", size=22, spacing_after=120),
        _paragraph(f"Покупатель\n(Заказчик): {customer_line}", size=22, spacing_after=120),
        _paragraph(f"Основание: {basis_line}", size=22, spacing_after=160),
        _invoice_items_table(line_items),
        _paragraph("", spacing_after=70),
        _invoice_totals_table(amount, currency),
        _paragraph("", spacing_after=40),
        _paragraph("\n".join(footer_lines), bold=False, align="left", size=22, spacing_after=220),
        _invoice_footer_signatures(),
        (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="{PAGE_MARGIN_TOP}" w:right="{PAGE_MARGIN_SIDE}" w:bottom="{PAGE_MARGIN_BOTTOM}" '
            f'w:left="{PAGE_MARGIN_SIDE}" w:header="{PAGE_HEADER_MARGIN}" w:footer="{PAGE_FOOTER_MARGIN}" w:gutter="0"/>'
            "</w:sectPr>"
        ),
    ]
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}</w:body>"
        "</w:document>"
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("docProps/core.xml", _document_core_properties_xml("Счет на оплату"))
        archive.writestr("docProps/app.xml", _app_properties_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _styles_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_relationships_xml())
    return output.getvalue()


def _generate_deal_service_document(
    *,
    deal: Deal,
    executor_company: Client,
    contract: SettlementContract | None | object = AUTO_CONTRACT,
    items: list[ActLineItem | dict],
    uploaded_by,
    document_type: str,
    settlement_title: str,
    original_label: str,
    file_prefix: str,
    builder,
    realization_status: str = "",
) -> tuple[DealDocument, SettlementDocument]:
    client = getattr(deal, "client", None)
    if client is None:
        raise ValidationError({"deal": "Для генерации документа у сделки должна быть выбрана компания."})
    line_items = [_coerce_line_item(item) for item in items]
    if not line_items:
        raise ValidationError({"items": "Добавьте хотя бы одну строку документа."})
    amount = sum((item.total for item in line_items), Decimal("0.00"))
    if amount <= 0:
        raise ValidationError({"items": "Сумма документа должна быть больше нуля."})

    with transaction.atomic():
        resolved_contract = contract
        if resolved_contract is AUTO_CONTRACT:
            resolved_contract = SettlementContract.objects.filter(client_id=client.pk, is_active=True).order_by("-created_at", "-id").first()
        if resolved_contract is not None and getattr(resolved_contract, "client_id", None) != client.pk:
            raise ValidationError({"contract": "Договор должен принадлежать компании сделки."})
        resolved_currency = (
            _normalize_text(getattr(resolved_contract, "currency", ""))
            or _normalize_text(getattr(client, "currency", ""))
            or _normalize_text(getattr(deal, "currency", ""))
            or "RUB"
        )
        settlement_document = SettlementDocument.objects.create(
            client=client,
            contract=resolved_contract,
            deal=deal,
            document_type=document_type,
            title=settlement_title,
            document_date=timezone.localdate(),
            currency=resolved_currency,
            amount=amount,
            generator_payload=_generator_payload(executor_company=executor_company, contract=resolved_contract, items=line_items),
            realization_status=realization_status,
        )

        file_name = _document_file_name(file_prefix=file_prefix, settlement_document=settlement_document)
        original_name = _document_original_name(original_label=original_label, settlement_document=settlement_document)
        document_bytes = builder(
            settlement_document=settlement_document,
            deal=deal,
            executor_company=executor_company,
            items=line_items,
        )
        settlement_document.original_name = original_name
        settlement_document.file.save(file_name, ContentFile(document_bytes, name=file_name), save=False)
        settlement_document.save(update_fields=["generator_payload", "file", "original_name", "updated_at"])

        content = ContentFile(document_bytes, name=file_name)
        deal_document = DealDocument(
            deal=deal,
            settlement_document=settlement_document,
            original_name=original_name,
            uploaded_by=uploaded_by,
        )
        deal_document.file.save(file_name, content, save=False)
        deal_document.save()
        return deal_document, settlement_document


def update_generated_deal_document(
    *,
    deal_document: DealDocument,
    executor_company: Client,
    contract: SettlementContract | None | object = AUTO_CONTRACT,
    items: list[ActLineItem | dict],
    uploaded_by=None,
) -> tuple[DealDocument, SettlementDocument]:
    settlement_document = resolve_settlement_document_for_deal_document(deal_document)
    if settlement_document is None:
        raise ValidationError({"deal_document": "Документ не связан со счетом или актом."})

    if settlement_document.document_type == SettlementDocument.DocumentType.INVOICE:
        settlement_title = "Счет на оплату"
        original_label = "Счет"
        file_prefix = "invoice"
        builder = build_invoice_docx_bytes
    elif settlement_document.document_type == SettlementDocument.DocumentType.REALIZATION:
        settlement_title = "Акт об оказании услуг"
        original_label = "Акт"
        file_prefix = "act"
        builder = build_act_docx_bytes
    else:
        raise ValidationError({"deal_document": "Редактирование доступно только для счета или акта."})

    deal = getattr(deal_document, "deal", None) or getattr(settlement_document, "deal", None)
    client = getattr(deal, "client", None) if deal is not None else None
    if deal is None or client is None:
        raise ValidationError({"deal_document": "Документ должен быть привязан к сделке и компании."})

    line_items = [_coerce_line_item(item) for item in items]
    if not line_items:
        raise ValidationError({"items": "Добавьте хотя бы одну строку документа."})
    amount = sum((item.total for item in line_items), Decimal("0.00"))
    if amount <= 0:
        raise ValidationError({"items": "Сумма документа должна быть больше нуля."})

    with transaction.atomic():
        resolved_contract = settlement_document.contract if contract is AUTO_CONTRACT else contract
        if resolved_contract is not None and getattr(resolved_contract, "client_id", None) != client.pk:
            raise ValidationError({"contract": "Договор должен принадлежать компании сделки."})
        settlement_document.client = client
        settlement_document.contract = resolved_contract
        settlement_document.deal = deal
        settlement_document.title = settlement_title
        settlement_document.amount = amount
        settlement_document.generator_payload = _generator_payload(executor_company=executor_company, contract=resolved_contract, items=line_items)
        settlement_document.save()

        file_name = _document_file_name(file_prefix=file_prefix, settlement_document=settlement_document)
        original_name = _document_original_name(original_label=original_label, settlement_document=settlement_document)
        document_bytes = builder(
            settlement_document=settlement_document,
            deal=deal,
            executor_company=executor_company,
            items=line_items,
        )
        settlement_document.original_name = original_name
        settlement_document.file.save(file_name, ContentFile(document_bytes, name=file_name), save=False)
        settlement_document.save(update_fields=["file", "original_name", "updated_at"])

        deal_document.deal = deal
        deal_document.settlement_document = settlement_document
        deal_document.original_name = original_name
        if uploaded_by is not None:
            deal_document.uploaded_by = uploaded_by
        deal_document.file.save(file_name, ContentFile(document_bytes, name=file_name), save=False)
        update_fields = ["deal", "settlement_document", "file", "original_name", "updated_at"]
        if uploaded_by is not None:
            update_fields.append("uploaded_by")
        deal_document.save(update_fields=update_fields)
        _append_generated_document_update_event(
            deal=deal,
            deal_document=deal_document,
            settlement_document=settlement_document,
            actor=uploaded_by,
        )
        return deal_document, settlement_document


def generate_deal_act(
    *,
    deal: Deal,
    executor_company: Client,
    contract: SettlementContract | None | object = AUTO_CONTRACT,
    items: list[ActLineItem | dict],
    uploaded_by=None,
) -> tuple[DealDocument, SettlementDocument]:
    return _generate_deal_service_document(
        deal=deal,
        executor_company=executor_company,
        contract=contract,
        items=items,
        uploaded_by=uploaded_by,
        document_type=SettlementDocument.DocumentType.REALIZATION,
        settlement_title="Акт об оказании услуг",
        original_label="Акт",
        file_prefix="act",
        builder=build_act_docx_bytes,
        realization_status=SettlementDocument.RealizationStatus.CREATED,
    )


def generate_deal_invoice(
    *,
    deal: Deal,
    executor_company: Client,
    contract: SettlementContract | None | object = AUTO_CONTRACT,
    items: list[ActLineItem | dict],
    uploaded_by=None,
) -> tuple[DealDocument, SettlementDocument]:
    return _generate_deal_service_document(
        deal=deal,
        executor_company=executor_company,
        contract=contract,
        items=items,
        uploaded_by=uploaded_by,
        document_type=SettlementDocument.DocumentType.INVOICE,
        settlement_title="Счет на оплату",
        original_label="Счет",
        file_prefix="invoice",
        builder=build_invoice_docx_bytes,
    )
