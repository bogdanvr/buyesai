from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.v1.automation_message_drafts.serializers import AutomationMessageDraftSerializer
from crm.models import AutomationMessageDraft
from crm.models.automation import AutomationMessageDraftStatus
from crm.services.automation_messages import send_automation_message_draft


class AutomationMessageDraftViewSet(ReadOnlyModelViewSet):
    serializer_class = AutomationMessageDraftSerializer

    def get_queryset(self):
        queryset = AutomationMessageDraft.objects.select_related(
            "automation_rule",
            "source_touch",
            "source_touch__channel",
            "source_touch__result_option",
            "proposed_channel",
            "owner",
            "lead",
            "deal",
            "client",
            "contact",
            "acted_by",
        ).prefetch_related("outbound_messages").order_by("status", "-created_at", "-id")
        status_value = self.request.query_params.get("status")
        deal_id = self.request.query_params.get("deal")
        client_id = self.request.query_params.get("client")
        lead_id = self.request.query_params.get("lead")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        return queryset

    def _mark_acted(self, draft, request, status_value):
        draft.status = status_value
        draft.acted_by = request.user if getattr(request.user, "is_authenticated", False) else None
        draft.acted_at = timezone.now()
        draft.save(update_fields=["status", "acted_by", "acted_at", "updated_at"])

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        draft = self.get_object()
        if draft.status != AutomationMessageDraftStatus.PENDING:
            return Response({"detail": "Черновик сообщения уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        self._mark_acted(draft, request, AutomationMessageDraftStatus.CONFIRMED)
        send_automation_message_draft(
            draft,
            acted_by=request.user if getattr(request.user, "is_authenticated", False) else None,
        )
        draft.refresh_from_db()
        return Response(self.get_serializer(draft).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        draft = self.get_object()
        if draft.status != AutomationMessageDraftStatus.PENDING:
            return Response({"detail": "Черновик сообщения уже обработан."}, status=status.HTTP_400_BAD_REQUEST)
        self._mark_acted(draft, request, AutomationMessageDraftStatus.DISMISSED)
        return Response(self.get_serializer(draft).data)
