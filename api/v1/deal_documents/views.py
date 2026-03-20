import mimetypes

from django.http import FileResponse, Http404
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet

from api.v1.deal_documents.serializers import DealDocumentSerializer
from crm.models import DealDocument


class DealDocumentViewSet(ModelViewSet):
    serializer_class = DealDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = DealDocument.objects.select_related("deal", "deal__client", "uploaded_by").order_by("-created_at", "-id")
        deal_id = self.request.query_params.get("deal")
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        instance = self.get_object()
        file_field = getattr(instance, "file", None)
        if not file_field:
            raise Http404("Файл не найден.")
        try:
            file_handle = file_field.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Файл не найден.") from exc

        filename = instance.original_name or file_field.name.rsplit("/", 1)[-1]
        content_type, _ = mimetypes.guess_type(filename)
        response = FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type or "application/octet-stream")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
