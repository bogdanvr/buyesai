from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from crm.models import Deal, DealDocument, SettlementContract, SettlementDocument


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


def _format_date_human(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return f"{value.day} {RUSSIAN_MONTHS.get(value.month, '')} {value.year} г."


def _format_date_short(value: date | None) -> str:
    if value is None:
        value = timezone.localdate()
    return value.strftime("%d.%m.%Y")


def _format_amount(value: Decimal | int | float | str) -> str:
    amount = Decimal(value or 0).quantize(Decimal("0.01"))
    formatted = f"{amount:,.2f}"
    return formatted.replace(",", " ").replace(".", ",")


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _build_party_details(name: str, requisites_parts: list[str]) -> str:
    normalized_parts = [part for part in (part.strip() for part in requisites_parts) if part]
    if not normalized_parts:
        return name
    return f"{name}, {', '.join(normalized_parts)}"


def _executor_details() -> tuple[str, str]:
    name = _normalize_text(getattr(settings, "CRM_ACT_EXECUTOR_NAME", "")) or "Исполнитель"
    requisites = _normalize_text(getattr(settings, "CRM_ACT_EXECUTOR_REQUISITES", "")) or "Реквизиты исполнителя не заполнены"
    return name, requisites


def _customer_details(deal: Deal) -> tuple[str, str]:
    client = deal.client
    if client is None:
        raise ValidationError({"deal": "Для генерации акта у сделки должна быть выбрана компания."})
    customer_name = _normalize_text(client.legal_name) or _normalize_text(client.name) or f"Компания #{client.pk}"
    account_value = _normalize_text(client.settlement_account or client.iban)
    account_label = "р/с" if _normalize_text(client.currency).upper() == "RUB" else "IBAN"
    requisites_parts = [
        f"ИНН {client.inn}" if client.inn else "",
        f"КПП {client.kpp}" if client.kpp else "",
        f"ОГРН {client.ogrn}" if client.ogrn else "",
        client.address or client.actual_address or "",
        f"{account_label} {account_value}" if account_value else "",
        f"БИК {client.bik}" if client.bik else "",
        f"к/с {client.correspondent_account}" if client.correspondent_account else "",
        client.bank_name or "",
        client.bank_details or "",
    ]
    return customer_name, _build_party_details(customer_name, requisites_parts)


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


def _service_table(service_name: str, amount: Decimal, currency: str) -> str:
    widths = [700, 4800, 1200, 900, 1600, 1700]
    headers = ["№", "Наименование работ, услуг", "Кол-во", "Ед.", "Цена", "Сумма"]
    header_xml = "".join(
        _table_cell(text, width=width, bold=True, align="center", shaded=True)
        for text, width in zip(headers, widths)
    )
    amount_text = _format_amount(amount)
    row_xml = "".join([
        _table_cell("1", width=widths[0], align="center"),
        _table_cell(service_name, width=widths[1]),
        _table_cell("1", width=widths[2], align="center"),
        _table_cell("усл.", width=widths[3], align="center"),
        _table_cell(amount_text, width=widths[4], align="right"),
        _table_cell(amount_text, width=widths[5], align="right"),
    ])
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
        f"<w:tr>{row_xml}</w:tr>"
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


def _document_xml(*, title: str, executor_line: str, customer_line: str, basis_line: str, service_name: str, amount: Decimal, currency: str) -> str:
    amount_text = _format_amount(amount)
    body = [
        _paragraph(title, bold=True, align="center", size=30, spacing_after=200),
        _paragraph(f"Исполнитель: {executor_line}", size=22),
        _paragraph(f"Заказчик: {customer_line}", size=22),
        _paragraph(f"Основание: {basis_line}", size=22, spacing_after=180),
        _service_table(service_name, amount, currency),
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


def build_act_docx_bytes(*, settlement_document: SettlementDocument, deal: Deal) -> bytes:
    executor_name, executor_requisites = _executor_details()
    customer_name, customer_line = _customer_details(deal)
    contract = getattr(settlement_document, "contract", None)
    basis_line = _normalize_text(getattr(contract, "number", "")) or _normalize_text(getattr(contract, "title", ""))
    if basis_line:
        basis_line = f"Договор {basis_line}"
    else:
        basis_line = f"Сделка «{_normalize_text(deal.title) or f'#{deal.pk}'}»"

    title = f"Акт об оказании услуг № {settlement_document.number} от {_format_date_human(settlement_document.document_date)}"
    service_name = _normalize_text(deal.title) or "Услуги по сделке"
    amount = Decimal(settlement_document.amount or 0)
    currency = _normalize_text(settlement_document.currency) or "RUB"
    document_xml = _document_xml(
        title=title,
        executor_line=_build_party_details(executor_name, [executor_requisites]),
        customer_line=customer_line,
        basis_line=basis_line,
        service_name=service_name,
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


def generate_deal_act(*, deal: Deal, uploaded_by=None) -> tuple[DealDocument, SettlementDocument]:
    client = getattr(deal, "client", None)
    if client is None:
        raise ValidationError({"deal": "Для генерации акта у сделки должна быть выбрана компания."})
    amount = Decimal(getattr(deal, "amount", 0) or 0)
    if amount <= 0:
        raise ValidationError({"deal": "Для генерации акта у сделки должна быть указана сумма больше нуля."})

    with transaction.atomic():
        contract = SettlementContract.objects.filter(client_id=client.pk, is_active=True).order_by("-created_at", "-id").first()
        settlement_document = SettlementDocument.objects.create(
            client=client,
            contract=contract,
            deal=deal,
            document_type=SettlementDocument.DocumentType.REALIZATION,
            title="Акт об оказании услуг",
            document_date=timezone.localdate(),
            currency=_normalize_text(getattr(deal, "currency", "")) or _normalize_text(getattr(client, "currency", "")) or "RUB",
            amount=amount,
            realization_status=SettlementDocument.RealizationStatus.CREATED,
        )

        file_name = f"act-{settlement_document.number or settlement_document.pk}.docx"
        original_name = f"Акт № {settlement_document.number} от {_format_date_short(settlement_document.document_date)}.docx"
        content = ContentFile(build_act_docx_bytes(settlement_document=settlement_document, deal=deal), name=file_name)
        deal_document = DealDocument(deal=deal, original_name=original_name, uploaded_by=uploaded_by)
        deal_document.file.save(file_name, content, save=False)
        deal_document.save()
        return deal_document, settlement_document
