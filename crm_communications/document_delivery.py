from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from crm.models import DealDocument
from crm_communications.models import Message, MessageAttachment


SOFFICE_CANDIDATE_PATHS = (
    "soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
    "/usr/lib64/libreoffice/program/soffice",
)


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


def _resolve_soffice_path() -> str:
    for candidate in SOFFICE_CANDIDATE_PATHS:
        resolved = shutil.which(candidate) if "/" not in candidate else (candidate if Path(candidate).exists() else "")
        if resolved:
            return str(resolved)
    raise ValidationError(
        {
            "deal_document": (
                "В системе недоступен LibreOffice (`soffice`) для конвертации документа в PDF. "
                "Установите пакет libreoffice/libreoffice-writer на сервере."
            )
        }
    )


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

    soffice_path = _resolve_soffice_path()

    with tempfile.TemporaryDirectory(prefix="deal-document-send-") as tmpdir:
        tmp_path = Path(tmpdir)
        source_path = tmp_path / (Path(original_name).name or f"document-{document.pk}{suffix or '.bin'}")
        source_path.write_bytes(source_bytes)
        output_dir = tmp_path / "pdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        profile_dir = tmp_path / "soffice-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    soffice_path,
                    f"-env:UserInstallation=file://{profile_dir}",
                    "--headless",
                    "--convert-to",
                    "pdf:writer_pdf_Export",
                    "--outdir",
                    str(output_dir),
                    str(source_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.CalledProcessError as exc:
            error_text = (exc.stderr or exc.stdout or "").strip() or str(exc)
            raise ValidationError({"deal_document": f"LibreOffice не смог сконвертировать документ в PDF: {error_text}"}) from exc
        except subprocess.TimeoutExpired as exc:
            raise ValidationError({"deal_document": "LibreOffice не успел сконвертировать документ в PDF."}) from exc

        pdf_path = output_dir / pdf_name
        if not pdf_path.exists():
            generated_candidates = sorted(output_dir.glob("*.pdf"))
            if generated_candidates:
                pdf_path = generated_candidates[0]
            else:
                raise ValidationError({"deal_document": "LibreOffice не создал PDF-файл."})
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
