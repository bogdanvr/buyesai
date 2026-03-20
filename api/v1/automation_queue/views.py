from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.v1.automation_queue.serializers import AutomationQueueItemSerializer
from crm.models import Activity, AutomationQueueItem
from crm.models.activity import ActivityType, TaskPriority, TaskStatus
from crm.models.automation import AutomationQueueItemKind, AutomationQueueItemStatus


class AutomationQueueItemViewSet(ReadOnlyModelViewSet):
    serializer_class = AutomationQueueItemSerializer

    def get_queryset(self):
        queryset = AutomationQueueItem.objects.select_related(
            "automation_rule",
            "source_touch",
            "source_touch__channel",
            "source_touch__result_option",
            "outcome",
            "touch_result",
            "next_step_template",
            "proposed_channel",
            "owner",
            "lead",
            "deal",
            "client",
            "contact",
            "task",
            "created_task",
            "acted_by",
        ).order_by("status", "-created_at", "-id")
        status_value = self.request.query_params.get("status")
        deal_id = self.request.query_params.get("deal")
        client_id = self.request.query_params.get("client")
        lead_id = self.request.query_params.get("lead")
        item_kind = self.request.query_params.get("item_kind")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        if item_kind:
            queryset = queryset.filter(item_kind=item_kind)
        return queryset

    def _mark_acted(self, item, request, status_value):
        item.status = status_value
        item.acted_by = request.user if getattr(request.user, "is_authenticated", False) else None
        item.acted_at = timezone.now()
        item.save(update_fields=["status", "acted_by", "acted_at", "updated_at"])

    def _create_task_from_item(self, item, request):
        if item.created_task_id:
            return item.created_task
        subject = str(item.proposed_next_step or item.recommended_action or item.title or "").strip()
        if not subject:
            return None
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject=subject,
            description=str(item.summary or "").strip(),
            due_at=item.proposed_next_step_at,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            communication_channel=item.proposed_channel,
            lead=item.lead,
            deal=item.deal,
            client=item.client,
            contact=item.contact,
            created_by=request.user if getattr(request.user, "is_authenticated", False) else item.owner,
        )
        item.created_task = task
        item.save(update_fields=["created_task", "updated_at"])
        return task

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        item = self.get_object()
        if item.status != AutomationQueueItemStatus.PENDING:
            return Response({"detail": "Элемент очереди уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        if item.item_kind == AutomationQueueItemKind.NEXT_STEP:
            self._create_task_from_item(item, request)
        self._mark_acted(item, request, AutomationQueueItemStatus.RESOLVED)
        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        item = self.get_object()
        if item.status != AutomationQueueItemStatus.PENDING:
            return Response({"detail": "Элемент очереди уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        self._mark_acted(item, request, AutomationQueueItemStatus.DISMISSED)
        serializer = self.get_serializer(item)
        return Response(serializer.data)
