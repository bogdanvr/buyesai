import mimetypes
from io import BytesIO

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.http import content_disposition_header
from django.views import View

from crm_communications.deal_document_shares import (
    build_share_download_url,
    build_share_public_url,
    record_share_page_open,
    record_share_pdf_download,
)
from crm_communications.document_delivery import build_deal_document_pdf_bytes
from crm_communications.models import DealDocumentShare


class DealDocumentSharePageView(View):
    template_name = "public_deal_document_share.html"

    def get(self, request, token: str):
        share = get_object_or_404(
            DealDocumentShare.objects.select_related(
                "document",
                "document__deal",
                "document__deal__client",
                "message",
            ),
            token=token,
        )
        record_share_page_open(share=share, request=request)
        share.refresh_from_db()
        document = share.document
        deal = getattr(document, "deal", None)
        company = getattr(deal, "client", None) if deal is not None else None
        context = {
            "share": share,
            "document": document,
            "deal": deal,
            "company": company,
            "public_url": build_share_public_url(share=share, request=request),
            "download_url": build_share_download_url(share=share, request=request),
        }
        return render(request, self.template_name, context=context)


class DealDocumentShareDownloadView(View):
    def get(self, request, token: str):
        share = get_object_or_404(
            DealDocumentShare.objects.select_related("document", "document__deal"),
            token=token,
        )
        try:
            pdf_bytes, pdf_name = build_deal_document_pdf_bytes(share.document)
        except FileNotFoundError as exc:
            raise Http404("Файл документа не найден.") from exc
        record_share_pdf_download(share=share, request=request)

        content_type, _ = mimetypes.guess_type(pdf_name)
        response = FileResponse(
            BytesIO(pdf_bytes),
            as_attachment=True,
            filename=pdf_name,
            content_type=content_type or "application/pdf",
        )
        response["Content-Disposition"] = content_disposition_header(True, pdf_name)
        return response
