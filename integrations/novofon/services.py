from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
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


def _phone_call_status_from_api(payload: dict) -> str:
    raw_status = str(payload.get("status") or payload.get("call_status") or "").strip().lower()
    if raw_status in {choice for choice, _label in PhoneCallStatus.choices}:
        return raw_status
    if raw_status in {"accepted", "initiated", "created"}:
        return PhoneCallStatus.RINGING
    if raw_status in {"error", "failed"}:
        return PhoneCallStatus.FAILED
    return PhoneCallStatus.RINGING


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
    if call.contact_id or call.company_id or call.lead_id or call.deal_id:
        return call

    binding = resolve_call_binding(account=account, phone_normalized=call.client_phone_normalized)
    call.contact = binding["contact"]
    call.company = binding["company"]
    call.lead = binding["lead"]
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
        event.retry_count = int(event.retry_count or 0) + 1
        event.save(update_fields=["status", "processed_at", "error_text", "retry_count"])
        return {"ok": False, "error": str(error)}


def reprocess_novofon_event(event: TelephonyEventLog) -> dict:
    event.retry_count = int(event.retry_count or 0) + 1
    event.status = TelephonyEventStatus.QUEUED
    event.error_text = ""
    event.save(update_fields=["retry_count", "status", "error_text"])
    return process_novofon_webhook_event(event)


def sync_novofon_employees(*, account: TelephonyProviderAccount | None = None) -> dict:
    account = account or get_novofon_account(create=True)
    if account is None:
        raise ValueError("Аккаунт Novofon не найден.")
    client = _provider_client(account)
    employees = client.list_employees()
    synced_ids = []
    for employee in employees:
        employee_id = str(employee.get("id") or employee.get("employee_id") or employee.get("uuid") or "").strip()
        if not employee_id:
            continue
        mapping, _created = TelephonyUserMapping.objects.get_or_create(
            provider_account=account,
            novofon_employee_id=employee_id,
            defaults={
                "novofon_extension": str(employee.get("extension") or employee.get("internal_number") or "").strip(),
                "novofon_full_name": str(employee.get("full_name") or employee.get("name") or "").strip(),
                "is_active": bool(employee.get("is_active", True)),
                "external_payload": employee,
            },
        )
        mapping.novofon_extension = str(employee.get("extension") or employee.get("internal_number") or mapping.novofon_extension or "").strip()
        mapping.novofon_full_name = str(employee.get("full_name") or employee.get("name") or mapping.novofon_full_name or "").strip()
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
        payload = client.ping()
        account.last_connection_checked_at = checked_at
        account.last_connection_status = "ok"
        account.last_connection_error = ""
        account.save(update_fields=["last_connection_checked_at", "last_connection_status", "last_connection_error", "updated_at"])
        return {"ok": True, "payload": payload}
    except NovofonClientError as error:
        account.last_connection_checked_at = checked_at
        account.last_connection_status = "error"
        account.last_connection_error = str(error)
        account.save(update_fields=["last_connection_checked_at", "last_connection_status", "last_connection_error", "updated_at"])
        return {"ok": False, "error": str(error)}


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
        response_payload.get("call_id")
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
