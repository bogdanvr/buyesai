from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.v1.automation_drafts.serializers import AutomationDraftSerializer
from crm.models import AutomationDraft
from crm.models.automation import AutomationDraftKind, AutomationDraftStatus


class AutomationDraftViewSet(ReadOnlyModelViewSet):
    serializer_class = AutomationDraftSerializer

    def get_queryset(self):
        queryset = AutomationDraft.objects.select_related(
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
            "acted_by",
        ).order_by("status", "-created_at", "-id")
        status_value = self.request.query_params.get("status")
        deal_id = self.request.query_params.get("deal")
        client_id = self.request.query_params.get("client")
        lead_id = self.request.query_params.get("lead")
        draft_kind = self.request.query_params.get("draft_kind")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        if draft_kind:
            queryset = queryset.filter(draft_kind=draft_kind)
        return queryset

    def _mark_acted(self, draft, request, status_value):
        draft.status = status_value
        draft.acted_by = request.user if getattr(request.user, "is_authenticated", False) else None
        draft.acted_at = timezone.now()
        draft.save(update_fields=["status", "acted_by", "acted_at", "updated_at"])

    def _apply_touch_draft(self, draft):
        touch = draft.source_touch
        if touch is None:
            return
        updated_fields = []
        if draft.touch_result_id and touch.result_option_id != draft.touch_result_id:
            touch.result_option_id = draft.touch_result_id
            updated_fields.append("result_option")
        if draft.proposed_channel_id and touch.channel_id != draft.proposed_channel_id:
            touch.channel_id = draft.proposed_channel_id
            updated_fields.append("channel")
        if draft.proposed_direction and touch.direction != draft.proposed_direction:
            touch.direction = draft.proposed_direction
            updated_fields.append("direction")
        if draft.summary and touch.summary != draft.summary:
            touch.summary = draft.summary
            updated_fields.append("summary")
        if draft.proposed_next_step and touch.next_step != draft.proposed_next_step:
            touch.next_step = draft.proposed_next_step
            updated_fields.append("next_step")
        if draft.proposed_next_step_at and touch.next_step_at != draft.proposed_next_step_at:
            touch.next_step_at = draft.proposed_next_step_at
            updated_fields.append("next_step_at")
        if draft.owner_id and touch.owner_id != draft.owner_id:
            touch.owner_id = draft.owner_id
            updated_fields.append("owner")
        if updated_fields:
            touch.save(update_fields=updated_fields + ["updated_at"])

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        draft = self.get_object()
        if draft.status != AutomationDraftStatus.PENDING:
            return Response({"detail": "Черновик уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        if draft.draft_kind in {AutomationDraftKind.TOUCH, AutomationDraftKind.NEXT_STEP}:
            self._apply_touch_draft(draft)
        self._mark_acted(draft, request, AutomationDraftStatus.CONFIRMED)
        serializer = self.get_serializer(draft)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        draft = self.get_object()
        if draft.status != AutomationDraftStatus.PENDING:
            return Response({"detail": "Черновик уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        self._mark_acted(draft, request, AutomationDraftStatus.DISMISSED)
        serializer = self.get_serializer(draft)
        return Response(serializer.data)
