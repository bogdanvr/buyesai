import logging

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.pagination import StandardResultsSetPagination
from integrations.models import PhoneCall, TelephonyEventLog
from integrations.novofon.client import NovofonClientError
from integrations.novofon.serializers import (
    NovofonCallRequestSerializer,
    NovofonCallImportRequestSerializer,
    NovofonSettingsSerializer,
    PhoneCallSerializer,
    TelephonyEventLogSerializer,
)
from integrations.novofon.security import validate_novofon_webhook_auth
from integrations.novofon.services import (
    check_novofon_connection,
    get_novofon_account,
    import_novofon_calls_history,
    initiate_novofon_call,
    queue_novofon_webhook_event,
    reprocess_novofon_event,
    sync_novofon_employees,
)


logger = logging.getLogger(__name__)


class NovofonSettingsAPIView(APIView):
    def get(self, request):
        account = get_novofon_account(create=True)
        return Response(NovofonSettingsSerializer(account).data)

    def put(self, request):
        account = get_novofon_account(create=True)
        serializer = NovofonSettingsSerializer(account, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(NovofonSettingsSerializer(account).data)


class NovofonCheckConnectionAPIView(APIView):
    def post(self, request):
        try:
            account = get_novofon_account(create=True)
            return Response(check_novofon_connection(account=account))
        except ValueError as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class NovofonSyncEmployeesAPIView(APIView):
    def post(self, request):
        try:
            account = get_novofon_account(create=True)
            result = sync_novofon_employees(account=account)
            payload = NovofonSettingsSerializer(account).data
            payload["sync_result"] = result
            return Response(payload)
        except (ValueError, NovofonClientError) as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            logger.exception("Unexpected error during Novofon employee sync")
            return Response({"ok": False, "error": str(error) or "unexpected_error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NovofonCallAPIView(APIView):
    def post(self, request):
        serializer = NovofonCallRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = initiate_novofon_call(user=request.user, **serializer.validated_data)
        except ValueError as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class NovofonImportCallsAPIView(APIView):
    def post(self, request):
        serializer = NovofonCallImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = get_novofon_account(create=True)
            result = import_novofon_calls_history(account=account, **serializer.validated_data)
        except ValueError as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class PhoneCallListAPIView(generics.ListAPIView):
    serializer_class = PhoneCallSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = PhoneCall.objects.select_related("crm_user", "responsible_user", "contact", "company", "lead", "deal").order_by("-started_at", "-created_at", "-id")
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        direction = self.request.query_params.get("direction")
        call_status = self.request.query_params.get("status")
        if entity_type and entity_id:
            field_name = {
                "contact": "contact_id",
                "company": "company_id",
                "lead": "lead_id",
                "deal": "deal_id",
            }.get(str(entity_type).strip())
            if field_name:
                queryset = queryset.filter(**{field_name: entity_id})
        if direction:
            queryset = queryset.filter(direction=direction)
        if call_status:
            queryset = queryset.filter(status=call_status)
        return queryset


class PhoneCallDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PhoneCallSerializer
    queryset = PhoneCall.objects.select_related("crm_user", "responsible_user", "contact", "company", "lead", "deal").all()


class TelephonyEventReprocessAPIView(APIView):
    def post(self, request, pk: int):
        event = TelephonyEventLog.objects.filter(pk=pk).first()
        if event is None:
            return Response({"detail": "Событие не найдено."}, status=status.HTTP_404_NOT_FOUND)
        result = reprocess_novofon_event(event)
        event.refresh_from_db()
        return Response({"event": TelephonyEventLogSerializer(event).data, "result": result}, status=status.HTTP_202_ACCEPTED)


class NovofonWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        account = get_novofon_account(create=True)
        payload = request.data if isinstance(request.data, dict) else {}
        headers = dict(request.headers.items())
        auth_error = validate_novofon_webhook_auth(
            payload=payload,
            headers=headers,
            api_secret=getattr(account, "api_secret", ""),
            webhook_shared_secret=getattr(account, "webhook_shared_secret", ""),
            query_secret=request.query_params.get("secret", ""),
        )
        if auth_error:
            return Response({"ok": False, "error": auth_error}, status=status.HTTP_403_FORBIDDEN)
        event = queue_novofon_webhook_event(payload=payload, headers=headers)
        return Response(
            {"ok": True, "event_id": event.pk, "queued": True, "status": event.status},
            status=status.HTTP_202_ACCEPTED,
        )
