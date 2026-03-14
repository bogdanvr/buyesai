from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.clients.serializers import ClientSerializer
from crm.selectors.client_selectors import list_clients


class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = list_clients()
        is_active = self.request.query_params.get("is_active")
        search_query = self.request.query_params.get("q")
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=is_active == "true")
        queryset = apply_text_search(
            queryset,
            search_query,
            ["name", "legal_name", "inn", "phone", "email", "address", "industry", "okved"],
        )
        return queryset
