from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from integrations.models import PhoneCallDirection, PhoneCallStatus
from integrations.novofon.selectors import normalize_phone


@dataclass(slots=True)
class ParsedNovofonEvent:
    event_type: str
    external_event_id: str
    external_call_id: str
    deduplication_key: str
    direction: str
    status: str
    phone_from: str
    phone_to: str
    client_phone_normalized: str
    virtual_number: str
    employee_id: str
    extension: str
    started_at: datetime | None
    answered_at: datetime | None
    ended_at: datetime | None
    duration_sec: int | None
    talk_duration_sec: int | None
    recording_url: str
    raw_payload: dict


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return ""


def _nested(payload: dict, *keys: str):
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _string(value) -> str:
    return str(value or "").strip()


def _parse_int(value) -> int | None:
    raw = _string(value)
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000.0
        return datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
    raw = _string(value)
    if not raw:
        return None
    if raw.isdigit():
        return _parse_timestamp(int(raw))
    parsed = parse_datetime(raw.replace("Z", "+00:00"))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone=dt_timezone.utc)
    return parsed


def _map_direction(value: str, event_type: str) -> str:
    raw = _string(value).lower()
    if raw in {"in", "inbound", "incoming"}:
        return PhoneCallDirection.INBOUND
    if raw in {"out", "outbound", "outgoing"}:
        return PhoneCallDirection.OUTBOUND
    if "out" in event_type:
        return PhoneCallDirection.OUTBOUND
    return PhoneCallDirection.INBOUND


def _map_status(value: str, event_type: str) -> str:
    raw = _string(value).lower()
    mapping = {
        "ringing": PhoneCallStatus.RINGING,
        "new": PhoneCallStatus.RINGING,
        "answered": PhoneCallStatus.ANSWERED,
        "connected": PhoneCallStatus.ANSWERED,
        "completed": PhoneCallStatus.COMPLETED,
        "ended": PhoneCallStatus.COMPLETED,
        "finished": PhoneCallStatus.COMPLETED,
        "missed": PhoneCallStatus.MISSED,
        "no_answer": PhoneCallStatus.MISSED,
        "busy": PhoneCallStatus.MISSED,
        "failed": PhoneCallStatus.FAILED,
        "error": PhoneCallStatus.FAILED,
        "canceled": PhoneCallStatus.CANCELED,
        "cancelled": PhoneCallStatus.CANCELED,
    }
    if raw in mapping:
        return mapping[raw]
    normalized_event = _string(event_type).lower()
    if "start" in normalized_event:
        return PhoneCallStatus.RINGING
    if "miss" in normalized_event or "no_answer" in normalized_event:
        return PhoneCallStatus.MISSED
    if "answer" in normalized_event:
        return PhoneCallStatus.ANSWERED
    if "end" in normalized_event:
        return PhoneCallStatus.COMPLETED
    if "complete" in normalized_event or "finish" in normalized_event:
        return PhoneCallStatus.COMPLETED
    if "cancel" in normalized_event:
        return PhoneCallStatus.CANCELED
    if "fail" in normalized_event:
        return PhoneCallStatus.FAILED
    return PhoneCallStatus.RINGING


def parse_novofon_webhook(payload: dict, headers: dict | None = None) -> ParsedNovofonEvent:
    payload = payload if isinstance(payload, dict) else {}
    call = payload.get("call") if isinstance(payload.get("call"), dict) else {}
    event_type = _string(_pick(payload.get("event_type"), payload.get("event"), payload.get("type"), call.get("event_type"), call.get("event")))
    external_event_id = _string(
        _pick(
            payload.get("event_id"),
            payload.get("id"),
            payload.get("webhook_id"),
            payload.get("notification_id"),
            call.get("event_id"),
        )
    )
    external_call_id = _string(
        _pick(
            payload.get("pbx_call_id"),
            payload.get("call_session_id"),
            payload.get("call_id"),
            payload.get("callId"),
            payload.get("communication_id"),
            payload.get("uniqueid"),
            payload.get("uuid"),
            call.get("pbx_call_id"),
            call.get("call_session_id"),
            call.get("call_id"),
            call.get("callId"),
            call.get("uniqueid"),
            call.get("uuid"),
            _nested(payload, "data", "call_id"),
        )
    )
    direction = _map_direction(_pick(payload.get("direction"), call.get("direction")), event_type)
    status = _map_status(
        _pick(
            payload.get("status"),
            call.get("status"),
            payload.get("call_status"),
            payload.get("disposition"),
            call.get("disposition"),
        ),
        event_type,
    )
    caller_phone = _string(
        _pick(
            payload.get("from"),
            payload.get("src"),
            payload.get("caller"),
            payload.get("caller_id"),
            payload.get("contact_phone_number"),
            call.get("from"),
            call.get("src"),
            call.get("caller"),
            call.get("caller_id"),
            call.get("contact_phone_number"),
        )
    )
    destination_phone = _string(
        _pick(
            payload.get("to"),
            payload.get("dst"),
            payload.get("callee"),
            payload.get("destination"),
            payload.get("contact_phone_number"),
            call.get("to"),
            call.get("dst"),
            call.get("callee"),
            call.get("destination"),
            call.get("contact_phone_number"),
        )
    )
    virtual_number = _string(
        _pick(
            payload.get("virtual_number"),
            payload.get("virtual_phone_number"),
            payload.get("did"),
            payload.get("called_did"),
            call.get("virtual_number"),
            call.get("virtual_phone_number"),
            call.get("did"),
            call.get("called_did"),
        )
    )
    employee_id = _string(
        _pick(
            payload.get("employee_id"),
            payload.get("manager_id"),
            payload.get("last_answered_employee_id"),
            payload.get("first_answered_employee_id"),
            call.get("employee_id"),
            call.get("manager_id"),
        )
    )
    extension = _string(
        _pick(
            payload.get("extension"),
            payload.get("internal_number"),
            payload.get("internal"),
            payload.get("operator_phone_number"),
            call.get("extension"),
            call.get("internal_number"),
            call.get("internal"),
            call.get("operator_phone_number"),
        )
    )
    started_at = _parse_timestamp(
        _pick(
            payload.get("started_at"),
            payload.get("start_time"),
            payload.get("call_start"),
            call.get("started_at"),
            call.get("start_time"),
            call.get("call_start"),
            payload.get("timestamp"),
            payload.get("notification_time"),
        )
    )
    answered_at = _parse_timestamp(
        _pick(
            payload.get("answered_at"),
            payload.get("answer_time"),
            call.get("answered_at"),
            call.get("answer_time"),
        )
    )
    ended_at = _parse_timestamp(
        _pick(
            payload.get("ended_at"),
            payload.get("end_time"),
            payload.get("call_end"),
            call.get("ended_at"),
            call.get("end_time"),
            call.get("call_end"),
            payload.get("notification_time"),
        )
    )
    duration_sec = _parse_int(
        _pick(
            payload.get("duration_sec"),
            payload.get("duration"),
            payload.get("total_duration"),
            call.get("duration_sec"),
            call.get("duration"),
            call.get("total_duration"),
        )
    )
    talk_duration_sec = _parse_int(
        _pick(
            payload.get("talk_duration_sec"),
            payload.get("talk_duration"),
            payload.get("clean_talk_duration"),
            payload.get("billsec"),
            call.get("talk_duration_sec"),
            call.get("talk_duration"),
            call.get("clean_talk_duration"),
            call.get("billsec"),
        )
    )
    recording_url = _string(
        _pick(
            payload.get("recording_url"),
            payload.get("record_url"),
            payload.get("full_record_file_link"),
            call.get("recording_url"),
            call.get("record_url"),
            call.get("full_record_file_link"),
        )
    )

    if direction == PhoneCallDirection.INBOUND:
        phone_from = caller_phone
        phone_to = virtual_number or destination_phone or extension
        client_phone_raw = caller_phone
    else:
        phone_from = extension or virtual_number or caller_phone
        phone_to = destination_phone or caller_phone
        client_phone_raw = destination_phone or caller_phone
    client_phone_normalized = normalize_phone(client_phone_raw)

    dedup_source = external_event_id or "|".join(
        [
            external_call_id,
            event_type,
            status,
            _string(started_at.isoformat() if started_at else ""),
            _string(ended_at.isoformat() if ended_at else ""),
        ]
    )
    deduplication_key = hashlib.sha256(dedup_source.encode("utf-8")).hexdigest() if dedup_source else ""

    return ParsedNovofonEvent(
        event_type=event_type,
        external_event_id=external_event_id,
        external_call_id=external_call_id,
        deduplication_key=deduplication_key,
        direction=direction,
        status=status,
        phone_from=phone_from,
        phone_to=phone_to,
        client_phone_normalized=client_phone_normalized,
        virtual_number=virtual_number,
        employee_id=employee_id,
        extension=extension,
        started_at=started_at,
        answered_at=answered_at,
        ended_at=ended_at,
        duration_sec=duration_sec,
        talk_duration_sec=talk_duration_sec,
        recording_url=recording_url,
        raw_payload=payload,
    )
