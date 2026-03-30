from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
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
    return (
        "<w:tc>"
        f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shading_xml}</w:tcPr>'
        f"{_paragraph(text, bold=bold, align=align, size=22, spacing_after=60)}"
        "</w:tc>"
    )


def _service_table(items: list[ActLineItem]) -> str:
    widths = [700, 4800, 1200, 900, 1600, 1700]
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
    amount_text = _format_amount(amount)
    body = [
        _paragraph(title, bold=True, align="center", size=30, spacing_after=200),
        _paragraph(f"Исполнитель: {executor_line}", size=22),
        _paragraph(f"Заказчик: {customer_line}", size=22),
        _paragraph(f"Основание: {basis_line}", size=22, spacing_after=180),
        _service_table(items),
        _paragraph("", spacing_after=80),
        _paragraph(f"Итого: {amount_text} {currency}", bold=True, align="right", size=24, spacing_after=160),
        _paragraph(f"Всего оказано услуг на сумму {amount_text} {currency}.", size=22),
        _paragraph("Вышеперечисленные услуги выполнены полностью и в срок. Заказчик претензий по объему, качеству и срокам оказания услуг не имеет.", size=22, spacing_after=260),
        _signatures_table(executor_line.split(',')[0], customer_line.split(',')[0]),
        (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="850" w:header="708" w:footer="708" w:gutter="0"/>'
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
    now_iso = timezone.now().replace(microsecond=0).isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Акт об оказании услуг</dc:title>"
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
        archive.writestr("docProps/core.xml", _core_properties_xml())
        archive.writestr("docProps/app.xml", _app_properties_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _styles_xml())
        archive.writestr("word/_rels/document.xml.rels", _document_relationships_xml())
    return output.getvalue()


def generate_deal_act(*, deal: Deal, executor_company: Client, items: list[ActLineItem | dict], uploaded_by=None) -> tuple[DealDocument, SettlementDocument]:
    client = getattr(deal, "client", None)
    if client is None:
        raise ValidationError({"deal": "Для генерации акта у сделки должна быть выбрана компания."})
    line_items = [_coerce_line_item(item) for item in items]
    if not line_items:
        raise ValidationError({"items": "Добавьте хотя бы одну строку акта."})
    amount = sum((item.total for item in line_items), Decimal("0.00"))
    if amount <= 0:
        raise ValidationError({"items": "Сумма акта должна быть больше нуля."})

    with transaction.atomic():
        contract = SettlementContract.objects.filter(client_id=client.pk, is_active=True).order_by("-created_at", "-id").first()
        resolved_currency = (
            _normalize_text(getattr(contract, "currency", ""))
            or _normalize_text(getattr(client, "currency", ""))
            or _normalize_text(getattr(deal, "currency", ""))
            or "RUB"
        )
        settlement_document = SettlementDocument.objects.create(
            client=client,
            contract=contract,
            deal=deal,
            document_type=SettlementDocument.DocumentType.REALIZATION,
            title="Акт об оказании услуг",
            document_date=timezone.localdate(),
            currency=resolved_currency,
            amount=amount,
            realization_status=SettlementDocument.RealizationStatus.CREATED,
        )

        file_name = f"act-{settlement_document.number or settlement_document.pk}.docx"
        original_name = f"Акт № {settlement_document.number} от {_format_date_short(settlement_document.document_date)}.docx"
        content = ContentFile(
            build_act_docx_bytes(
                settlement_document=settlement_document,
                deal=deal,
                executor_company=executor_company,
                items=line_items,
            ),
            name=file_name,
        )
        deal_document = DealDocument(deal=deal, original_name=original_name, uploaded_by=uploaded_by)
        deal_document.file.save(file_name, content, save=False)
        deal_document.save()
        return deal_document, settlement_document
