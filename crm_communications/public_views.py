import mimetypes
import json
from io import BytesIO

from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.utils.http import content_disposition_header
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from crm_communications.deal_document_shares import (
    build_share_download_url,
    build_share_event_url,
    build_share_preview_url,
    build_share_public_url,
    record_share_pdf_download,
    record_share_viewer_event,
)
from crm_communications.document_delivery import build_deal_document_pdf_bytes
from crm_communications.models import DealDocumentShare, DealDocumentShareEventType


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
        document = share.document
        deal = getattr(document, "deal", None)
        company = getattr(deal, "client", None) if deal is not None else None
        context = {
            "share": share,
            "document": document,
            "deal": deal,
            "company": company,
            "public_url": build_share_public_url(share=share, request=request),
            "preview_url": build_share_preview_url(share=share, request=request),
            "event_url": build_share_event_url(share=share, request=request),
            "download_url": build_share_download_url(share=share, request=request),
        }
        return render(request, self.template_name, context=context)


class DealDocumentSharePreviewView(View):
    def get(self, request, token: str):
        share = get_object_or_404(
            DealDocumentShare.objects.select_related("document", "document__deal"),
            token=token,
        )
        try:
            pdf_bytes, pdf_name = build_deal_document_pdf_bytes(share.document)
        except FileNotFoundError as exc:
            raise Http404("Файл документа не найден.") from exc

        content_type, _ = mimetypes.guess_type(pdf_name)
        response = FileResponse(
            BytesIO(pdf_bytes),
            as_attachment=False,
            filename=pdf_name,
            content_type=content_type or "application/pdf",
        )
        response["Content-Disposition"] = content_disposition_header(False, pdf_name)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class DealDocumentShareEventView(View):
    allowed_event_types = {
        DealDocumentShareEventType.DOCUMENT_OPENED,
        DealDocumentShareEventType.PAGE_VIEWED,
        DealDocumentShareEventType.LAST_PAGE_REACHED,
        DealDocumentShareEventType.VIEWER_CLOSED,
        DealDocumentShareEventType.TIME_IN_VIEWER,
    }

    def post(self, request, token: str):
        share = get_object_or_404(
            DealDocumentShare.objects.select_related("document", "document__deal", "message"),
            token=token,
        )
        try:
            payload = json.loads((request.body or b"{}").decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return HttpResponseBadRequest("Некорректный JSON.")

        event_type = str(payload.get("event_type") or "").strip()
        metadata = payload.get("metadata") if isinstance(payload, dict) else {}
        if event_type not in self.allowed_event_types:
            return HttpResponseBadRequest("Неподдерживаемый тип события.")

        event = record_share_viewer_event(
            share=share,
            request=request,
            event_type=event_type,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        return JsonResponse(
            {
                "id": event.pk,
                "event_type": event.event_type,
                "happened_at": event.happened_at.isoformat(),
            },
            status=201,
        )


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
