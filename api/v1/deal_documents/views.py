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
