from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.touches.serializers import TouchSerializer
from crm.models import Touch


class TouchViewSet(ModelViewSet):
    serializer_class = TouchSerializer

    def get_queryset(self):
        queryset = Touch.objects.select_related(
            "channel", "owner", "lead", "lead__client", "deal", "deal__client", "client", "contact", "contact__client", "task"
        ).order_by("-happened_at", "-id")
        lead_id = self.request.query_params.get("lead")
        deal_id = self.request.query_params.get("deal")
        client_id = self.request.query_params.get("client")
        contact_id = self.request.query_params.get("contact")
        task_id = self.request.query_params.get("task")
        search_query = self.request.query_params.get("q")
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        queryset = apply_text_search(queryset, search_query, ["summary", "next_step"])
        return queryset
