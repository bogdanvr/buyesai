from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from audit.services import log_event
from crm.models import Activity, Client, Contact, Deal, Lead
from crm.models.activity import ActivityType, TaskPriority, TaskStatus
from integrations.models import (
    PhoneCall,
    PhoneCallDirection,
    PhoneCallStatus,
    TelephonyEventLog,
    TelephonyEventStatus,
    TelephonyProvider,
    TelephonyProviderAccount,
    TelephonyUserMapping,
)
from integrations.novofon.client import NovofonClient, NovofonClientError
from integrations.novofon.selectors import (
    build_webhook_url,
    get_novofon_account,
    normalize_phone,
    resolve_call_binding,
    resolve_novofon_mapping,
)
from integrations.novofon.webhook_parser import ParsedNovofonEvent, parse_novofon_webhook


logger = logging.getLogger(__name__)
User = get_user_model()


ENTITY_MODELS: dict[str, Any] = {
    "contact": Contact,
    "company": Client,
    "lead": Lead,
    "deal": Deal,
}


def _provider_client(account: TelephonyProviderAccount) -> NovofonClient:
    return NovofonClient(account)


CALLS_REPORT_FIELDS = [
    "id",
    "start_time",
    "finish_time",
    "direction",
    "is_lost",
    "contact_phone_number",
    "virtual_phone_number",
    "operator_phone_number",
    "talk_duration",
    "clean_talk_duration",
    "total_duration",
    "full_record_file_link",
    "communication_id",
    "last_answered_employee_id",
    "first_answered_employee_id",
    "last_talked_employee_id",
    "first_talked_employee_id",
    "employees",
]


def _phone_call_status_from_api(payload: dict) -> str:
    raw_status = str(payload.get("status") or payload.get("call_status") or "").strip().lower()
    if raw_status in {choice for choice, _label in PhoneCallStatus.choices}:
        return raw_status
    if raw_status in {"accepted", "initiated", "created"}:
        return PhoneCallStatus.RINGING
    if raw_status in {"error", "failed"}:
        return PhoneCallStatus.FAILED
    return PhoneCallStatus.RINGING


def _resolve_novofon_timezone(account: TelephonyProviderAccount):
    timezone_name = str((account.settings_json or {}).get("novofon_timezone") or "").strip()
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except Exception:
            logger.warning("Invalid Novofon timezone in settings_json: %s", timezone_name)
    return timezone.get_current_timezone()


def _parse_novofon_datetime(value: str, *, source_timezone=None):
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = parse_datetime(raw.replace(" ", "T"))
    if parsed is None:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, source_timezone or timezone.get_current_timezone())
    return parsed


def _int_or_none(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _phone_call_status_from_report(row: dict) -> str:
    if bool(row.get("is_lost")):
        return PhoneCallStatus.MISSED
    total_duration = _int_or_none(row.get("total_duration")) or 0
    talk_duration = _int_or_none(row.get("talk_duration")) or 0
    finish_time = _parse_novofon_datetime(row.get("finish_time"))
    if talk_duration > 0:
        return PhoneCallStatus.COMPLETED
    if finish_time and total_duration == 0:
        return PhoneCallStatus.CANCELED
    if finish_time:
        return PhoneCallStatus.COMPLETED
    return PhoneCallStatus.RINGING


def _direction_from_report(row: dict) -> str:
    return PhoneCallDirection.INBOUND if str(row.get("direction") or "").strip().lower() == "in" else PhoneCallDirection.OUTBOUND


def _resolve_history_employee_id(row: dict) -> str:
    candidates = [
        row.get("last_answered_employee_id"),
        row.get("last_talked_employee_id"),
        row.get("first_answered_employee_id"),
        row.get("first_talked_employee_id"),
    ]
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    employees = row.get("employees") if isinstance(row.get("employees"), list) else []
    for employee in employees:
        normalized = str((employee or {}).get("employee_id") or "").strip()
        if normalized:
            return normalized
    return ""


def _upsert_phone_call_from_history(*, account: TelephonyProviderAccount, row: dict, source_timezone=None) -> tuple[PhoneCall | None, bool]:
    external_call_id = str(row.get("id") or "").strip()
    if not external_call_id:
        return None, False

    direction = _direction_from_report(row)
    employee_id = _resolve_history_employee_id(row)
    mapping = resolve_novofon_mapping(account=account, employee_id=employee_id)
    phone_from = str(
        row.get("contact_phone_number")
        if direction == PhoneCallDirection.INBOUND
        else (row.get("operator_phone_number") or row.get("virtual_phone_number") or "")
    ).strip()
    phone_to = str(
        (row.get("virtual_phone_number") or row.get("operator_phone_number") or "")
        if direction == PhoneCallDirection.INBOUND
        else row.get("contact_phone_number")
    ).strip()
    normalized_client_phone = normalize_phone(row.get("contact_phone_number") or "")
    call, created = PhoneCall.objects.get_or_create(
        provider=TelephonyProvider.NOVOFON,
        external_call_id=external_call_id,
        defaults={
            "external_parent_event_id": str(row.get("communication_id") or "").strip(),
            "direction": direction,
            "status": _phone_call_status_from_report(row),
            "phone_from": phone_from,
            "phone_to": phone_to,
            "client_phone_normalized": normalized_client_phone,
            "virtual_number": str(row.get("virtual_phone_number") or "").strip(),
            "crm_user": getattr(mapping, "crm_user", None),
            "responsible_user": getattr(mapping, "crm_user", None) or account.default_owner,
            "started_at": _parse_novofon_datetime(row.get("start_time"), source_timezone=source_timezone),
            "answered_at": _parse_novofon_datetime(row.get("start_time"), source_timezone=source_timezone) if (_int_or_none(row.get("talk_duration")) or 0) > 0 else None,
            "ended_at": _parse_novofon_datetime(row.get("finish_time"), source_timezone=source_timezone),
            "duration_sec": _int_or_none(row.get("total_duration")),
            "talk_duration_sec": _int_or_none(row.get("clean_talk_duration")) or _int_or_none(row.get("talk_duration")),
            "recording_url": str(row.get("full_record_file_link") or "").strip(),
            "raw_payload_last": row,
        },
    )
    call.external_parent_event_id = str(row.get("communication_id") or call.external_parent_event_id or "").strip()
    call.direction = direction
    call.status = _phone_call_status_from_report(row)
    call.phone_from = phone_from or call.phone_from
    call.phone_to = phone_to or call.phone_to
    call.client_phone_normalized = normalized_client_phone or call.client_phone_normalized
    call.virtual_number = str(row.get("virtual_phone_number") or call.virtual_number or "").strip()
    call.crm_user = getattr(mapping, "crm_user", None) or call.crm_user
    call.responsible_user = getattr(mapping, "crm_user", None) or call.responsible_user or account.default_owner
    call.started_at = _parse_novofon_datetime(row.get("start_time"), source_timezone=source_timezone) or call.started_at
    if (_int_or_none(row.get("talk_duration")) or 0) > 0:
        call.answered_at = _parse_novofon_datetime(row.get("start_time"), source_timezone=source_timezone) or call.answered_at
    call.ended_at = _parse_novofon_datetime(row.get("finish_time"), source_timezone=source_timezone) or call.ended_at
    call.duration_sec = _int_or_none(row.get("total_duration")) if row.get("total_duration") not in (None, "") else call.duration_sec
    call.talk_duration_sec = (
        _int_or_none(row.get("clean_talk_duration"))
        or _int_or_none(row.get("talk_duration"))
        or call.talk_duration_sec
    )
    call.recording_url = str(row.get("full_record_file_link") or call.recording_url or "").strip()
    call.raw_payload_last = row or call.raw_payload_last
    _ensure_binding_for_call(account=account, call=call)
    call.save()
    return call, created


def _resolve_entity(*, entity_type: str, entity_id: int):
    model = ENTITY_MODELS.get(str(entity_type or "").strip())
    if model is None:
        raise ValueError("Некорректный тип сущности.")
    instance = model.objects.filter(pk=entity_id).first()
    if instance is None:
        raise ValueError("CRM-сущность не найдена.")
    return instance


def _apply_entity_binding(call: PhoneCall, *, entity_type: str, instance) -> PhoneCall:
    if entity_type == "contact":
        call.contact = instance
        call.company = instance.client
    elif entity_type == "company":
        call.company = instance
    elif entity_type == "lead":
        call.lead = instance
        call.company = instance.client
        call.responsible_user = call.responsible_user or instance.assigned_to
    elif entity_type == "deal":
        call.deal = instance
        call.company = instance.client
        call.lead = instance.lead
        call.responsible_user = call.responsible_user or instance.owner
    return call


def _create_unknown_lead(*, account: TelephonyProviderAccount, phone_normalized: str, raw_phone: str, responsible_user=None) -> Lead:
    lead = Lead.objects.create(
        title=f"Неизвестный звонок {raw_phone or phone_normalized}",
        phone=raw_phone or phone_normalized,
        assigned_to=responsible_user or account.default_owner,
    )
    return lead


def _ensure_binding_for_call(*, account: TelephonyProviderAccount, call: PhoneCall) -> PhoneCall:
    binding = resolve_call_binding(account=account, phone_normalized=call.client_phone_normalized)
    if call.contact_id is None and binding["contact"] is not None:
        call.contact = binding["contact"]
    if call.company_id is None and binding["company"] is not None:
        call.company = binding["company"]
    if call.lead_id is None and binding["lead"] is not None:
        call.lead = binding["lead"]
    if call.deal_id is None and binding["deal"] is not None:
        call.deal = binding["deal"]
    if call.responsible_user_id is None:
        call.responsible_user = (
            getattr(call.deal, "owner", None)
            or getattr(call.lead, "assigned_to", None)
            or account.default_owner
        )
    if (
        call.contact_id is None
        and call.company_id is None
        and call.lead_id is None
        and account.create_lead_for_unknown_number
        and call.client_phone_normalized
    ):
        raw_phone = call.phone_from if call.direction == PhoneCallDirection.INBOUND else call.phone_to
        lead = _create_unknown_lead(
            account=account,
            phone_normalized=call.client_phone_normalized,
            raw_phone=raw_phone,
            responsible_user=call.responsible_user,
        )
        call.lead = lead
    return call


def _upsert_phone_call_from_event(*, account: TelephonyProviderAccount, parsed: ParsedNovofonEvent) -> PhoneCall:
    if not parsed.external_call_id:
        raise ValueError("В webhook отсутствует устойчивый внешний ID звонка.")

    mapping = resolve_novofon_mapping(
        account=account,
        employee_id=parsed.employee_id,
        extension=parsed.extension,
    )
    call, _created = PhoneCall.objects.get_or_create(
        provider=TelephonyProvider.NOVOFON,
        external_call_id=parsed.external_call_id,
        defaults={
            "external_parent_event_id": parsed.external_event_id,
            "direction": parsed.direction,
            "status": parsed.status,
            "phone_from": parsed.phone_from,
            "phone_to": parsed.phone_to,
            "client_phone_normalized": parsed.client_phone_normalized,
            "virtual_number": parsed.virtual_number,
            "crm_user": getattr(mapping, "crm_user", None),
            "responsible_user": getattr(mapping, "crm_user", None) or account.default_owner,
            "started_at": parsed.started_at,
            "answered_at": parsed.answered_at,
            "ended_at": parsed.ended_at,
            "duration_sec": parsed.duration_sec,
            "talk_duration_sec": parsed.talk_duration_sec,
            "recording_url": parsed.recording_url,
            "raw_payload_last": parsed.raw_payload,
        },
    )

    call.external_parent_event_id = parsed.external_event_id or call.external_parent_event_id
    call.direction = parsed.direction or call.direction
    call.status = parsed.status or call.status
    call.phone_from = parsed.phone_from or call.phone_from
    call.phone_to = parsed.phone_to or call.phone_to
    call.client_phone_normalized = parsed.client_phone_normalized or call.client_phone_normalized
    call.virtual_number = parsed.virtual_number or call.virtual_number
    call.crm_user = getattr(mapping, "crm_user", None) or call.crm_user
    call.responsible_user = getattr(mapping, "crm_user", None) or call.responsible_user or account.default_owner
    call.started_at = parsed.started_at or call.started_at
    call.answered_at = parsed.answered_at or call.answered_at
    call.ended_at = parsed.ended_at or call.ended_at
    call.duration_sec = parsed.duration_sec if parsed.duration_sec is not None else call.duration_sec
    call.talk_duration_sec = parsed.talk_duration_sec if parsed.talk_duration_sec is not None else call.talk_duration_sec
    call.recording_url = parsed.recording_url or call.recording_url
    call.raw_payload_last = parsed.raw_payload or call.raw_payload_last
    _ensure_binding_for_call(account=account, call=call)
    call.save()
    return call


def create_missed_call_followup_task(call: PhoneCall):
    if call.status != PhoneCallStatus.MISSED:
        return None
    marker = f"missed_call:{call.external_call_id}"
    existing = Activity.objects.filter(
        type=ActivityType.TASK,
        description__icontains=marker,
    ).first()
    if existing is not None:
        return existing
    due_at = timezone.now()
    return Activity.objects.create(
        type=ActivityType.TASK,
        subject="Перезвонить по пропущенному звонку",
        description=f"Автосоздано по пропущенному звонку {call.external_call_id}\n{marker}",
        due_at=due_at,
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        created_by=call.responsible_user or call.crm_user,
        client=call.company,
        contact=call.contact,
        lead=call.lead,
        deal=call.deal,
    )


def refresh_call_recording_if_needed(call: PhoneCall):
    return {"ok": True, "recording_url": call.recording_url}


def queue_novofon_webhook_event(*, payload: dict, headers: dict | None = None) -> TelephonyEventLog:
    parsed = parse_novofon_webhook(payload, headers or {})
    return TelephonyEventLog.objects.create(
        provider=TelephonyProvider.NOVOFON,
        event_type=parsed.event_type,
        external_event_id=parsed.external_event_id,
        external_call_id=parsed.external_call_id,
        deduplication_key=parsed.deduplication_key,
        payload_json=payload if isinstance(payload, dict) else {},
        headers_json=headers or {},
        status=TelephonyEventStatus.QUEUED,
    )


def requeue_novofon_event(event: TelephonyEventLog) -> dict:
    event.status = TelephonyEventStatus.QUEUED
    event.processed_at = None
    event.error_text = ""
    event.save(update_fields=["status", "processed_at", "error_text"])
    return {"ok": True, "queued": True, "event_id": event.pk}


def _novofon_failed_retry_backoff_seconds(*, retry_count: int, base_seconds: int = 30, max_seconds: int = 900) -> int:
    normalized_retry_count = max(1, int(retry_count or 1))
    normalized_base = max(1, int(base_seconds or 30))
    normalized_max = max(normalized_base, int(max_seconds or 900))
    return min(normalized_max, normalized_base * (2 ** max(0, normalized_retry_count - 1)))


def _claim_ready_event_ids(
    *,
    limit: int,
    retry_failed: bool,
    max_retries: int | None,
    failed_backoff_base_seconds: int,
    failed_backoff_max_seconds: int,
    reclaim_stale_processing_after_seconds: int | None,
) -> list[int]:
    now = timezone.now()
    selected_event_ids: list[int] = []
    seen_event_ids: set[int] = set()

    def _append_event_ids(ids):
        for event_id in ids:
            normalized_event_id = int(event_id)
            if normalized_event_id in seen_event_ids:
                continue
            seen_event_ids.add(normalized_event_id)
            selected_event_ids.append(normalized_event_id)
            if len(selected_event_ids) >= limit:
                break

    queued_queryset = (
        TelephonyEventLog.objects
        .select_for_update(skip_locked=True)
        .filter(provider=TelephonyProvider.NOVOFON, status=TelephonyEventStatus.QUEUED)
        .order_by("received_at", "id")
    )
    if max_retries is not None:
        queued_queryset = queued_queryset.filter(retry_count__lt=max(1, int(max_retries)))
    _append_event_ids(queued_queryset.values_list("id", flat=True)[:limit])

    remaining_slots = limit - len(selected_event_ids)
    if retry_failed and remaining_slots > 0:
        failed_queryset = (
            TelephonyEventLog.objects
            .select_for_update(skip_locked=True)
            .filter(provider=TelephonyProvider.NOVOFON, status=TelephonyEventStatus.FAILED)
            .order_by("processed_at", "received_at", "id")
        )
        if max_retries is not None:
            failed_queryset = failed_queryset.filter(retry_count__lt=max(1, int(max_retries)))
        failed_candidates = list(failed_queryset[: max(remaining_slots * 4, remaining_slots)])
        ready_failed_ids = []
        for event in failed_candidates:
            retry_at = (event.processed_at or event.received_at) + timedelta(
                seconds=_novofon_failed_retry_backoff_seconds(
                    retry_count=event.retry_count,
                    base_seconds=failed_backoff_base_seconds,
                    max_seconds=failed_backoff_max_seconds,
                )
            )
            if retry_at <= now:
                ready_failed_ids.append(event.pk)
        _append_event_ids(ready_failed_ids)

    remaining_slots = limit - len(selected_event_ids)
    normalized_reclaim_seconds = None
    if reclaim_stale_processing_after_seconds is not None and int(reclaim_stale_processing_after_seconds or 0) > 0:
        normalized_reclaim_seconds = int(reclaim_stale_processing_after_seconds)
    if normalized_reclaim_seconds and remaining_slots > 0:
        stale_before = now - timedelta(seconds=normalized_reclaim_seconds)
        processing_queryset = (
            TelephonyEventLog.objects
            .select_for_update(skip_locked=True)
            .filter(
                provider=TelephonyProvider.NOVOFON,
                status=TelephonyEventStatus.PROCESSING,
                processed_at__isnull=False,
                processed_at__lte=stale_before,
            )
            .order_by("processed_at", "received_at", "id")
        )
        if max_retries is not None:
            processing_queryset = processing_queryset.filter(retry_count__lt=max(1, int(max_retries)))
        _append_event_ids(processing_queryset.values_list("id", flat=True)[:remaining_slots])

    return selected_event_ids


def claim_novofon_events_for_processing(
    *,
    limit: int = 25,
    retry_failed: bool = False,
    max_retries: int | None = None,
    failed_backoff_base_seconds: int = 30,
    failed_backoff_max_seconds: int = 900,
    reclaim_stale_processing_after_seconds: int | None = 300,
) -> list[TelephonyEventLog]:
    normalized_limit = max(1, int(limit or 25))

    with transaction.atomic():
        event_ids = _claim_ready_event_ids(
            limit=normalized_limit,
            retry_failed=retry_failed,
            max_retries=max_retries,
            failed_backoff_base_seconds=failed_backoff_base_seconds,
            failed_backoff_max_seconds=failed_backoff_max_seconds,
            reclaim_stale_processing_after_seconds=reclaim_stale_processing_after_seconds,
        )
        if not event_ids:
            return []
        (
            TelephonyEventLog.objects
            .filter(pk__in=event_ids)
            .update(
                status=TelephonyEventStatus.PROCESSING,
                processed_at=timezone.now(),
                error_text="",
                retry_count=F("retry_count") + 1,
            )
        )
    return list(TelephonyEventLog.objects.filter(pk__in=event_ids).order_by("received_at", "id"))


@transaction.atomic
def process_novofon_webhook_event(event: TelephonyEventLog) -> dict:
    account = get_novofon_account(create=True)
    if account is None:
        raise ValueError("Аккаунт Novofon не инициализирован.")

    parsed = parse_novofon_webhook(event.payload_json or {}, event.headers_json or {})
    duplicate = (
        TelephonyEventLog.objects
        .exclude(pk=event.pk)
        .filter(provider=TelephonyProvider.NOVOFON, deduplication_key=parsed.deduplication_key)
        .filter(status__in=[TelephonyEventStatus.PROCESSED, TelephonyEventStatus.IGNORED_DUPLICATE])
        .exists()
    )
    if duplicate and parsed.deduplication_key:
        event.status = TelephonyEventStatus.IGNORED_DUPLICATE
        event.processed_at = timezone.now()
        event.error_text = ""
        event.save(update_fields=["status", "processed_at", "error_text"])
        return {"ok": True, "duplicate": True}

    try:
        call = _upsert_phone_call_from_event(account=account, parsed=parsed)
        if account.create_task_for_missed_call and call.status == PhoneCallStatus.MISSED:
            create_missed_call_followup_task(call)
        event.status = TelephonyEventStatus.PROCESSED
        event.processed_at = timezone.now()
        event.error_text = ""
        event.save(update_fields=["status", "processed_at", "error_text"])
        return {"ok": True, "call_id": call.pk, "external_call_id": call.external_call_id}
    except Exception as error:
        logger.exception("Failed to process Novofon webhook event id=%s", event.pk)
        event.status = TelephonyEventStatus.FAILED
        event.processed_at = timezone.now()
        event.error_text = str(error)
        event.save(update_fields=["status", "processed_at", "error_text"])
        return {"ok": False, "error": str(error)}


def process_novofon_webhook_queue(
    *,
    limit: int = 25,
    retry_failed: bool = False,
    max_retries: int | None = None,
    failed_backoff_base_seconds: int = 30,
    failed_backoff_max_seconds: int = 900,
    reclaim_stale_processing_after_seconds: int | None = 300,
) -> dict:
    events = claim_novofon_events_for_processing(
        limit=limit,
        retry_failed=retry_failed,
        max_retries=max_retries,
        failed_backoff_base_seconds=failed_backoff_base_seconds,
        failed_backoff_max_seconds=failed_backoff_max_seconds,
        reclaim_stale_processing_after_seconds=reclaim_stale_processing_after_seconds,
    )
    results = []
    processed = 0
    succeeded = 0
    failed = 0
    duplicates = 0
    for event in events:
        result = process_novofon_webhook_event(event)
        processed += 1
        if result.get("duplicate"):
            duplicates += 1
        elif result.get("ok"):
            succeeded += 1
        else:
            failed += 1
        results.append({"event_id": event.pk, "result": result})
    return {
        "ok": True,
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "duplicates": duplicates,
        "results": results,
    }


def reprocess_novofon_event(event: TelephonyEventLog) -> dict:
    return requeue_novofon_event(event)


def sync_novofon_employees(*, account: TelephonyProviderAccount | None = None) -> dict:
    account = account or get_novofon_account(create=True)
    if account is None:
        raise ValueError("Аккаунт Novofon не найден.")
    client = _provider_client(account)
    employees = client.list_employees()
    synced_ids = []
    extension_max_length = TelephonyUserMapping._meta.get_field("novofon_extension").max_length or 64
    employee_id_max_length = TelephonyUserMapping._meta.get_field("novofon_employee_id").max_length or 128
    full_name_max_length = TelephonyUserMapping._meta.get_field("novofon_full_name").max_length or 255
    for employee in employees:
        if not isinstance(employee, dict):
            continue
        employee_id = str(employee.get("id") or employee.get("employee_id") or employee.get("uuid") or "").strip()[:employee_id_max_length]
        if not employee_id:
            continue
        extension_payload = employee.get("extension") if isinstance(employee.get("extension"), dict) else {}
        extension_value = str(
            employee.get("phone_number")
            or employee.get("extension_phone_number")
            or employee.get("inner_phone_number")
            or extension_payload.get("extension_phone_number")
            or extension_payload.get("inner_phone_number")
            or employee.get("extension")
            or ""
        ).strip()[:extension_max_length]
        full_name = str(employee.get("full_name") or employee.get("name") or "").strip()[:full_name_max_length]
        mapping, _created = TelephonyUserMapping.objects.get_or_create(
            provider_account=account,
            novofon_employee_id=employee_id,
            defaults={
                "novofon_extension": extension_value,
                "novofon_full_name": full_name,
                "is_active": bool(employee.get("is_active", True)),
                "external_payload": employee,
            },
        )
        mapping.novofon_extension = extension_value or mapping.novofon_extension or ""
        mapping.novofon_full_name = full_name or mapping.novofon_full_name or ""
        mapping.is_active = bool(employee.get("is_active", True))
        mapping.external_payload = employee
        mapping.save()
        synced_ids.append(mapping.pk)
    return {"ok": True, "count": len(synced_ids), "mapping_ids": synced_ids}


def check_novofon_connection(*, account: TelephonyProviderAccount | None = None) -> dict:
    account = account or get_novofon_account(create=True)
    if account is None:
        raise ValueError("Аккаунт Novofon не найден.")
    client = _provider_client(account)
    checked_at = timezone.now()
    try:
        data_api_payload = client.ping()
        call_api_payload = client.probe_call_api()
        virtual_numbers = client.list_virtual_numbers()
        account_data = (data_api_payload.get("data") or [{}])[0] if isinstance(data_api_payload.get("data"), list) else {}
        novofon_timezone = str(account_data.get("timezone") or "").strip()
        settings_json = dict(account.settings_json or {})
        if novofon_timezone:
            settings_json["novofon_timezone"] = novofon_timezone
            account.settings_json = settings_json
        account.last_connection_checked_at = checked_at
        account.last_connection_status = "ok"
        account.last_connection_error = ""
        account.save(update_fields=["settings_json", "last_connection_checked_at", "last_connection_status", "last_connection_error", "updated_at"])
        return {
            "ok": True,
            "payload": {
                "data_api": data_api_payload,
                "call_api": call_api_payload,
                "virtual_numbers_count": len(virtual_numbers),
            },
        }
    except NovofonClientError as error:
        account.last_connection_checked_at = checked_at
        account.last_connection_status = "error"
        account.last_connection_error = str(error)
        account.save(update_fields=["last_connection_checked_at", "last_connection_status", "last_connection_error", "updated_at"])
        return {"ok": False, "error": str(error)}


@transaction.atomic
def import_novofon_calls_history(
    *,
    account: TelephonyProviderAccount | None = None,
    date_from=None,
    date_till=None,
    days: int = 30,
    limit: int = 500,
    max_records: int = 5000,
    include_ongoing_calls: bool = False,
) -> dict:
    account = account or get_novofon_account(create=True)
    if account is None or not account.enabled:
        raise ValueError("Интеграция Novofon отключена.")

    now = timezone.now()
    resolved_date_till = date_till or now
    resolved_date_from = date_from or (resolved_date_till - timedelta(days=int(days or 30)))
    if resolved_date_from > resolved_date_till:
        raise ValueError("date_from не может быть больше date_till.")
    if resolved_date_till - resolved_date_from > timedelta(days=90):
        raise ValueError("Novofon Data API позволяет импортировать период не более 90 дней за один запуск.")

    client = _provider_client(account)
    source_timezone = _resolve_novofon_timezone(account)
    imported = 0
    created_count = 0
    updated_count = 0
    missed_followups = 0
    offset = 0
    normalized_limit = max(1, min(int(limit or 500), 1000))
    normalized_max_records = max(1, min(int(max_records or 5000), 20000))

    while imported < normalized_max_records:
        requested_limit = min(normalized_limit, normalized_max_records - imported)
        page = client.get_calls_report(
            date_from=resolved_date_from,
            date_till=resolved_date_till,
            limit=requested_limit,
            offset=offset,
            include_ongoing_calls=include_ongoing_calls,
            fields=CALLS_REPORT_FIELDS,
        )
        records = page.get("data") if isinstance(page.get("data"), list) else []
        if not records:
            break
        for row in records:
            call, created = _upsert_phone_call_from_history(account=account, row=row, source_timezone=source_timezone)
            if call is None:
                continue
            imported += 1
            if created:
                created_count += 1
            else:
                updated_count += 1
            if account.create_task_for_missed_call and call.status == PhoneCallStatus.MISSED:
                followup = create_missed_call_followup_task(call)
                if followup is not None:
                    missed_followups += 1
            if imported >= normalized_max_records:
                break
        if len(records) < requested_limit:
            break
        offset += len(records)

    return {
        "ok": True,
        "date_from": resolved_date_from.isoformat(),
        "date_till": resolved_date_till.isoformat(),
        "imported": imported,
        "created": created_count,
        "updated": updated_count,
        "missed_followups": missed_followups,
        "limit": normalized_limit,
        "max_records": normalized_max_records,
    }


@transaction.atomic
def initiate_novofon_call(*, user, phone: str, entity_type: str, entity_id: int, comment: str = "") -> dict:
    account = get_novofon_account(create=True)
    if account is None or not account.enabled:
        raise ValueError("Интеграция Novofon отключена.")

    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        raise ValueError("Некорректный номер телефона.")

    mapping = resolve_novofon_mapping(account=account, crm_user=user)
    if mapping is None:
        raise ValueError("Для текущего пользователя не настроено сопоставление с сотрудником Novofon.")

    instance = _resolve_entity(entity_type=entity_type, entity_id=entity_id)
    call = PhoneCall.objects.create(
        provider=TelephonyProvider.NOVOFON,
        direction=PhoneCallDirection.OUTBOUND,
        status=PhoneCallStatus.RINGING,
        phone_from=mapping.novofon_extension,
        phone_to=phone,
        client_phone_normalized=normalized_phone,
        crm_user=user,
        responsible_user=user,
        raw_payload_last={"comment": comment, "request_phone": phone},
    )
    _apply_entity_binding(call, entity_type=entity_type, instance=instance)
    call.save()

    client = _provider_client(account)
    try:
        response_payload = client.initiate_call(
            employee_id=mapping.novofon_employee_id,
            extension=mapping.novofon_extension,
            phone=phone,
            comment=comment,
            external_context={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "phone_call_id": call.pk,
            },
        )
    except NovofonClientError as error:
        call.status = PhoneCallStatus.FAILED
        call.raw_payload_last = {"error": str(error)}
        call.save(update_fields=["status", "raw_payload_last", "updated_at"])
        raise ValueError(f"Novofon API вернул ошибку: {error}") from error

    call.external_call_id = str(
        response_payload.get("call_session_id")
        or response_payload.get("call_id")
        or response_payload.get("id")
        or response_payload.get("uuid")
        or call.external_call_id
        or ""
    ).strip()
    call.status = _phone_call_status_from_api(response_payload)
    call.raw_payload_last = response_payload
    call.started_at = call.started_at or timezone.now()
    call.save()

    log_event(
        action="novofon.call.initiated",
        app_label="integrations",
        model="phonecall",
        object_id=call.pk,
        payload={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "external_call_id": call.external_call_id,
            "phone": phone,
            "webhook_url": build_webhook_url(account),
        },
        actor=user,
    )
    return {
        "ok": True,
        "phone_call_id": call.pk,
        "external_call_id": call.external_call_id,
        "status": call.status,
    }
