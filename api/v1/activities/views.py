from django.db.models import Q
from rest_framework.viewsets import ModelViewSet

from api.v1.filters import apply_text_search
from api.v1.activities.serializers import ActivitySerializer
from crm.models import Activity
from crm.models.activity import ActivityType, TaskStatus


class ActivityViewSet(ModelViewSet):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        queryset = Activity.objects.select_related(
            "lead", "deal", "client", "contact", "created_by", "task_type", "task_type__category", "communication_channel", "related_touch"
        ).order_by("-created_at")
        type_code = self.request.query_params.get("type")
        exclude_type = self.request.query_params.get("exclude_type")
        deal_id = self.request.query_params.get("deal")
        client_id = self.request.query_params.get("client")
        is_done = self.request.query_params.get("is_done")
        status = self.request.query_params.get("status")
        search_query = self.request.query_params.get("q")
        if type_code:
            queryset = queryset.filter(type=type_code)
        if exclude_type:
            queryset = queryset.exclude(type=exclude_type)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if status:
            queryset = queryset.filter(status=status)
        if is_done in {"true", "false"}:
            if type_code == ActivityType.TASK or exclude_type == ActivityType.TASK:
                if is_done == "true":
                    queryset = queryset.filter(status=TaskStatus.DONE)
                else:
                    queryset = queryset.filter(status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])
            else:
                queryset = queryset.filter(
                    Q(
                        type=ActivityType.TASK,
                        status__in=[TaskStatus.DONE] if is_done == "true" else [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
                    )
                    | ~Q(type=ActivityType.TASK)
                )
        queryset = apply_text_search(queryset, search_query, ["subject", "description"])
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=serializer.validated_data.get("created_by") or user)
