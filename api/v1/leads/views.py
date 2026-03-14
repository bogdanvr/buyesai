from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.leads.serializers import LeadSerializer
from crm.selectors.lead_selectors import list_leads


class LeadViewSet(ModelViewSet):
    serializer_class = LeadSerializer

    def get_queryset(self):
        queryset = list_leads()
        status_code = self.request.query_params.get("status")
        source_code = self.request.query_params.get("source")
        search_query = self.request.query_params.get("q")

        if status_code:
            queryset = queryset.filter(status__code=status_code)
        if source_code:
            queryset = queryset.filter(source__code=source_code)
        queryset = apply_text_search(
            queryset,
            search_query,
            ["title", "name", "phone", "email", "company", "external_id"],
        )
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
