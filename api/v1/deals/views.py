from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.deals.serializers import DealSerializer
from crm.selectors.deal_selectors import list_deals


class DealViewSet(ModelViewSet):
    serializer_class = DealSerializer

    def get_queryset(self):
        queryset = list_deals()
        client_id = self.request.query_params.get("client")
        stage_code = self.request.query_params.get("stage")
        is_won = self.request.query_params.get("is_won")
        search_query = self.request.query_params.get("q")

        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if stage_code:
            queryset = queryset.filter(stage__code=stage_code)
        if is_won in {"true", "false"}:
            queryset = queryset.filter(is_won=is_won == "true")
        queryset = apply_text_search(queryset, search_query, ["title", "client__name"])
        return queryset
