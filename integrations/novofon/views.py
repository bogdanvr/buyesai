import json
import logging
import re
from datetime import timedelta
from urllib.parse import parse_qsl

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.pagination import StandardResultsSetPagination
from integrations.models import PhoneCall, PhoneCallTranscriptionStatus, TelephonyEventLog, TelephonyEventStatus, TelephonyProvider
from integrations.novofon.client import NovofonClientError
from integrations.novofon.serializers import (
    IncomingPhoneCallPopupSerializer,
    NovofonCallRequestSerializer,
    NovofonCallImportRequestSerializer,
    NovofonSettingsSerializer,
    PhoneCallSerializer,
    TelephonyEventLogSerializer,
)
from integrations.novofon.security import validate_novofon_webhook_auth
from integrations.novofon.services import (
    _resolve_novofon_timezone,
    check_novofon_connection,
    get_novofon_account,
    import_novofon_calls_history,
    initiate_novofon_call,
    process_novofon_webhook_event,
    queue_novofon_webhook_event,
    reprocess_novofon_event,
    sync_novofon_employees,
)
from integrations.soniox.services import refresh_phone_call_transcription


logger = logging.getLogger(__name__)


def _refresh_pending_transcriptions(calls):
    for call in calls:
        if str(getattr(call, "transcription_external_id", "") or "").strip() and getattr(call, "transcription_status", "") in {
            PhoneCallTranscriptionStatus.QUEUED,
            PhoneCallTranscriptionStatus.PROCESSING,
        }:
            try:
                refresh_phone_call_transcription(call)
            except Exception as error:
                logger.warning("Failed to refresh Soniox transcription for call id=%s: %s", getattr(call, "pk", None), error)


def _normalize_novofon_scalar(value):
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    while len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'"', "'"}:
        normalized = normalized[1:-1].strip()
    return normalized


def _normalize_novofon_payload(payload):
    if isinstance(payload, dict):
        return {
            str(key or "").strip(): _normalize_novofon_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_normalize_novofon_payload(item) for item in payload]
    return _normalize_novofon_scalar(payload)


def _unwrap_embedded_json_payload(payload: dict) -> dict:
    if not isinstance(payload, dict) or len(payload) != 1:
        return payload
    (single_key, single_value), = payload.items()
    candidate = str(single_key or "").strip()
    if str(single_value or "").strip():
        return payload
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return payload
    parsed_json = _parse_embedded_json_candidate(candidate)
    if parsed_json is None:
        return payload
    return parsed_json if isinstance(parsed_json, dict) else payload


def _repair_embedded_json_candidate(candidate: str) -> str:
    return re.sub(
        r'(:\s*)""([^"]*)""(?=\s*[,}])',
        lambda match: match.group(1) + json.dumps(f'"{match.group(2)}"'),
        candidate,
    )


def _parse_embedded_json_candidate(candidate: str):
    try:
        return json.loads(candidate)
    except (TypeError, ValueError):
        repaired_candidate = _repair_embedded_json_candidate(candidate)
        if repaired_candidate == candidate:
            return None
        try:
            return json.loads(repaired_candidate)
        except (TypeError, ValueError):
            return None


def _parse_novofon_request_payload(request) -> dict:
    raw_body = request.body.decode("utf-8", errors="ignore").strip()
    if not raw_body:
        return {}

    try:
        parsed_json = json.loads(raw_body)
        if isinstance(parsed_json, dict):
            return _normalize_novofon_payload(_unwrap_embedded_json_payload(parsed_json))
    except (TypeError, ValueError):
        pass

    parsed_pairs = parse_qsl(raw_body, keep_blank_values=True)
    if parsed_pairs:
        parsed_form = {str(key or "").strip(): value for key, value in parsed_pairs}
        return _normalize_novofon_payload(_unwrap_embedded_json_payload(parsed_form))

    return {}


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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            items = list(page)
            _refresh_pending_transcriptions(items)
            serializer = self.get_serializer(items, many=True)
            return self.get_paginated_response(serializer.data)
        items = list(queryset)
        _refresh_pending_transcriptions(items)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class PhoneCallDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PhoneCallSerializer
    queryset = PhoneCall.objects.select_related("crm_user", "responsible_user", "contact", "company", "lead", "deal").all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        _refresh_pending_transcriptions([instance])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class IncomingPhoneCallPopupAPIView(APIView):
    def get(self, request):
        raw_after_id = request.query_params.get("after_id")
        raw_limit = request.query_params.get("limit")
        try:
            after_id = max(0, int(raw_after_id or 0))
        except (TypeError, ValueError):
            after_id = 0
        try:
            limit = min(50, max(1, int(raw_limit or 20)))
        except (TypeError, ValueError):
            limit = 20

        queryset = (
            PhoneCall.objects
            .select_related("responsible_user", "contact", "company", "lead", "deal")
            .filter(provider="novofon", direction="inbound")
            .filter(Q(crm_user=request.user) | Q(responsible_user=request.user))
            .order_by("id")
        )
        latest_call_id = queryset.order_by("-id").values_list("id", flat=True).first() or 0
        if after_id <= 0:
            return Response({"ok": True, "items": [], "next_call_id": latest_call_id, "has_more": False})

        items = list(queryset.filter(pk__gt=after_id)[:limit])
        next_call_id = items[-1].pk if items else after_id
        has_more = queryset.filter(pk__gt=next_call_id).exists()
        return Response(
            {
                "ok": True,
                "items": IncomingPhoneCallPopupSerializer(items, many=True).data,
                "next_call_id": next_call_id,
                "has_more": has_more,
            }
        )


class TelephonyHealthAPIView(APIView):
    def get(self, request):
        stale_processing_after_seconds = 300
        stale_before = timezone.now() - timedelta(seconds=stale_processing_after_seconds)
        queryset = TelephonyEventLog.objects.filter(provider=TelephonyProvider.NOVOFON)
        latest_event = queryset.order_by("-received_at", "-id").first()
        problem_events = list(
            queryset
            .filter(
                Q(status=TelephonyEventStatus.FAILED)
                | Q(status=TelephonyEventStatus.QUEUED)
                | Q(status=TelephonyEventStatus.PROCESSING)
            )
            .order_by("-received_at", "-id")[:10]
        )
        serialized_problem_events = []
        for event in problem_events:
            item = TelephonyEventLogSerializer(event).data
            item["is_stale_processing"] = bool(
                event.status == TelephonyEventStatus.PROCESSING
                and event.processed_at is not None
                and event.processed_at <= stale_before
            )
            serialized_problem_events.append(item)
        oldest_queued = queryset.filter(status=TelephonyEventStatus.QUEUED).order_by("received_at", "id").first()
        payload = {
            "ok": True,
            "provider": TelephonyProvider.NOVOFON,
            "counts": {
                "queued": queryset.filter(status=TelephonyEventStatus.QUEUED).count(),
                "failed": queryset.filter(status=TelephonyEventStatus.FAILED).count(),
                "processing": queryset.filter(status=TelephonyEventStatus.PROCESSING).count(),
                "stale_processing": queryset.filter(
                    status=TelephonyEventStatus.PROCESSING,
                    processed_at__isnull=False,
                    processed_at__lte=stale_before,
                ).count(),
                "processed": queryset.filter(status=TelephonyEventStatus.PROCESSED).count(),
                "ignored_duplicate": queryset.filter(status=TelephonyEventStatus.IGNORED_DUPLICATE).count(),
            },
            "latest_event_at": getattr(latest_event, "received_at", None),
            "oldest_queued_at": getattr(oldest_queued, "received_at", None),
            "stale_processing_after_seconds": stale_processing_after_seconds,
            "problem_events": serialized_problem_events,
        }
        return Response(payload)


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
        payload = _parse_novofon_request_payload(request)
        headers = dict(request.headers.items())
        if not payload:
            return Response({"ok": False, "error": "invalid_payload"}, status=status.HTTP_400_BAD_REQUEST)
        auth_error = validate_novofon_webhook_auth(
            payload=payload,
            headers=headers,
            api_secret=getattr(account, "api_secret", ""),
            webhook_shared_secret=getattr(account, "webhook_shared_secret", ""),
            query_secret=request.query_params.get("secret", ""),
        )
        if auth_error:
            return Response({"ok": False, "error": auth_error}, status=status.HTTP_403_FORBIDDEN)
        event = queue_novofon_webhook_event(payload=payload, headers=headers, account=account)
        result = process_novofon_webhook_event(event)
        event.refresh_from_db()
        return Response(
            {
                "ok": True,
                "event_id": event.pk,
                "queued": event.status == TelephonyEventStatus.QUEUED,
                "status": event.status,
                "processed_immediately": True,
                "result": result,
            },
            status=status.HTTP_202_ACCEPTED,
        )
