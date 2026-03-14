from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.activities.serializers import ActivitySerializer
from crm.models import Activity


class ActivityViewSet(ModelViewSet):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        queryset = Activity.objects.select_related(
            "lead", "deal", "client", "contact", "created_by"
        ).order_by("-created_at")
        type_code = self.request.query_params.get("type")
        deal_id = self.request.query_params.get("deal")
        is_done = self.request.query_params.get("is_done")
        search_query = self.request.query_params.get("q")
        if type_code:
            queryset = queryset.filter(type=type_code)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if is_done in {"true", "false"}:
            queryset = queryset.filter(is_done=is_done == "true")
        queryset = apply_text_search(queryset, search_query, ["subject", "description"])
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
