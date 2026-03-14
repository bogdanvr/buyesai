from rest_framework.viewsets import ModelViewSet

from api.v1.contacts.serializers import ContactSerializer
from api.v1.filters import apply_text_search
from crm.models import Contact


class ContactViewSet(ModelViewSet):
    serializer_class = ContactSerializer

    def get_queryset(self):
        queryset = Contact.objects.select_related("client").order_by("-created_at")
        client_id = self.request.query_params.get("client")
        is_primary = self.request.query_params.get("is_primary")
        search_query = self.request.query_params.get("q")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if is_primary in {"true", "false"}:
            queryset = queryset.filter(is_primary=is_primary == "true")
        queryset = apply_text_search(
            queryset,
            search_query,
            ["first_name", "last_name", "phone", "email", "position", "client__name"],
        )
        return queryset
