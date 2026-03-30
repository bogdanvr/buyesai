from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from crm.models import DealDocument
from crm_communications.models import Message, MessageAttachment


TEXTUTIL_PATH = "/usr/bin/textutil"
CUPSFILTER_PATH = "/usr/sbin/cupsfilter"


def _normalized_original_name(document: DealDocument) -> str:
    file_field = getattr(document, "file", None)
    fallback_name = ""
    if file_field:
        fallback_name = Path(str(file_field.name or "")).name
    return str(document.original_name or fallback_name or f"document-{document.pk}").strip()


def _pdf_name_for_document(document: DealDocument) -> str:
    original_name = _normalized_original_name(document)
    stem = Path(original_name).stem or f"document-{document.pk}"
    return f"{stem}.pdf"


def build_deal_document_pdf_bytes(document: DealDocument) -> tuple[bytes, str]:
    file_field = getattr(document, "file", None)
    if not file_field:
        raise ValidationError({"deal_document": "У документа сделки отсутствует файл."})

    original_name = _normalized_original_name(document)
    suffix = Path(original_name).suffix.lower()
    pdf_name = _pdf_name_for_document(document)

    try:
        file_field.open("rb")
        source_bytes = file_field.read()
    finally:
        try:
            file_field.close()
        except Exception:
            pass

    if not source_bytes:
        raise ValidationError({"deal_document": "Файл документа сделки пустой."})

    if suffix == ".pdf":
        return source_bytes, pdf_name

    if not (Path(TEXTUTIL_PATH).exists() and Path(CUPSFILTER_PATH).exists()):
        raise ValidationError({"deal_document": "В системе недоступна конвертация документа в PDF."})

    with tempfile.TemporaryDirectory(prefix="deal-document-send-") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / (Path(original_name).name or f"document-{document.pk}{suffix or '.bin'}")
        source_path.write_bytes(source_bytes)

        text_path = tmp_path / "source.txt"
        try:
            subprocess.run(
                [TEXTUTIL_PATH, "-convert", "txt", "-output", str(text_path), str(source_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            error_text = (exc.stderr or exc.stdout or "").strip() or str(exc)
            raise ValidationError({"deal_document": f"Не удалось подготовить текст документа для PDF: {error_text}"}) from exc

        pdf_path = tmp_path / pdf_name
        try:
            with pdf_path.open("wb") as pdf_handle:
                subprocess.run(
                    [CUPSFILTER_PATH, "-i", "text/plain", "-m", "application/pdf", str(text_path)],
                    check=True,
                    stdout=pdf_handle,
                    stderr=subprocess.PIPE,
                    text=False,
                )
        except subprocess.CalledProcessError as exc:
            error_text = ""
            if isinstance(exc.stderr, bytes):
                error_text = exc.stderr.decode("utf-8", errors="ignore").strip()
            else:
                error_text = str(exc.stderr or "").strip()
            raise ValidationError({"deal_document": f"Не удалось сконвертировать документ в PDF: {error_text or exc}"}) from exc

        if not pdf_path.exists():
            raise ValidationError({"deal_document": "PDF-файл не был создан."})
        return pdf_path.read_bytes(), pdf_name


def attach_deal_document_pdf_to_message(*, message: Message, document: DealDocument) -> MessageAttachment:
    pdf_bytes, pdf_name = build_deal_document_pdf_bytes(document)
    attachment = MessageAttachment(
        message=message,
        original_name=pdf_name[:255],
        mime_type="application/pdf",
        size_bytes=len(pdf_bytes),
    )
    attachment.file.save(pdf_name, ContentFile(pdf_bytes, name=pdf_name), save=False)
    attachment.save()
    return attachment
