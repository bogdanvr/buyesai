import mimetypes

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from django.utils.http import content_disposition_header
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from api.v1.deal_documents.serializers import DealActGenerateSerializer, DealDocumentSerializer
from crm.models import DealDocument
from crm.services.act_generation import generate_deal_act


class DealDocumentViewSet(ModelViewSet):
    serializer_class = DealDocumentSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = DealDocument.objects.select_related("deal", "deal__client", "uploaded_by").order_by("-created_at", "-id")
        deal_id = self.request.query_params.get("deal")
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate-act")
    def generate_act(self, request):
        request_serializer = DealActGenerateSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        try:
            deal_document, _ = generate_deal_act(
                deal=request_serializer.validated_data["deal"],
                executor_company=request_serializer.validated_data["executor_company"],
                items=request_serializer.validated_data["items"],
                uploaded_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or {"detail": str(exc)})

        serializer = self.get_serializer(deal_document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        response["Content-Disposition"] = content_disposition_header(False, filename)
        return response
