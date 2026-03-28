from __future__ import annotations

import base64
import hashlib
import hmac


def _string(value) -> str:
    return str(value or "").strip()


def _nested(payload: dict, *keys: str):
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _pick(*values):
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return ""


def _normalize_event_name(payload: dict) -> str:
    return _string(
        _pick(
            payload.get("event"),
            payload.get("event_type"),
            payload.get("type"),
        )
    ).upper()


def _payload_signature_source(payload: dict) -> str:
    event_name = _normalize_event_name(payload)
    call_start = _string(
        _pick(
            payload.get("call_start"),
            payload.get("notification_time"),
            payload.get("start_time"),
            payload.get("started_at"),
            _nested(payload, "call", "call_start"),
        )
    )
    caller_phone = _string(
        _pick(
            payload.get("caller_id"),
            payload.get("from"),
            payload.get("contact_phone_number"),
            _nested(payload, "contact_info", "contact_phone_number"),
            _nested(payload, "call", "from"),
        )
    )
    called_phone = _string(
        _pick(
            payload.get("called_did"),
            payload.get("virtual_phone_number"),
            payload.get("destination"),
            payload.get("to"),
            _nested(payload, "contact_info", "communication_number"),
            _nested(payload, "call", "to"),
        )
    )
    internal_phone = _string(
        _pick(
            payload.get("internal"),
            payload.get("extension"),
            payload.get("operator_phone_number"),
            _nested(payload, "employee_info", "extension_phone_number"),
            _nested(payload, "call", "extension"),
        )
    )
    pbx_call_id = _string(_pick(payload.get("pbx_call_id"), payload.get("call_session_id"), payload.get("call_id")))
    call_id_with_rec = _string(
        _pick(
            payload.get("call_id_with_rec"),
            payload.get("record_id"),
            payload.get("recording_id"),
            _nested(payload, "record_info", "call_id_with_rec"),
        )
    )
    result_value = payload.get("result")

    if event_name in {"NOTIFY_START", "NOTIFY_IN_START", "NOTIFY_INTERNAL", "NOTIFY_END", "NOTIFY_IVR"}:
        return f"{caller_phone}{called_phone}{call_start}"
    if event_name in {"NOTIFY_ANSWER", "CALL_START", "CALL_END"}:
        return f"{caller_phone}{called_phone}{call_start}"
    if event_name in {"NOTIFY_OUT_START", "NOTIFY_OUT_END"}:
        return f"{internal_phone}{called_phone}{call_start}"
    if event_name in {"NOTIFY_RECORD", "RECORD_CALL"}:
        return f"{pbx_call_id}{call_id_with_rec}"
    if event_name in {"NUMBER_LOOKUP", "CALL_TRACKING", "SMS"}:
        return _string(result_value)
    return ""


def build_novofon_webhook_signature(payload: dict, *, secret: str) -> str:
    source = _payload_signature_source(payload if isinstance(payload, dict) else {})
    normalized_secret = _string(secret)
    if not source or not normalized_secret:
        return ""
    digest = hmac.new(normalized_secret.encode("utf-8"), source.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_novofon_webhook_signature(payload: dict, *, provided_signature: str, secret: str) -> bool:
    expected = build_novofon_webhook_signature(payload, secret=secret)
    if not expected:
        return False
    normalized_provided = _string(provided_signature)
    if not normalized_provided:
        return False
    return hmac.compare_digest(expected, normalized_provided)


def _header_value(headers: dict | None, *names: str) -> str:
    normalized_headers = {str(key).strip().lower(): value for key, value in (headers or {}).items()}
    for name in names:
        value = normalized_headers.get(str(name).strip().lower())
        if value not in (None, ""):
            return _string(value)
    return ""


def extract_novofon_webhook_signature(headers: dict | None) -> str:
    return _header_value(
        headers,
        "Signature",
        "X-Signature",
        "X-Novofon-Signature",
    )


def validate_novofon_webhook_auth(
    *,
    payload: dict,
    headers: dict | None = None,
    api_secret: str = "",
    webhook_shared_secret: str = "",
    query_secret: str = "",
) -> str:
    normalized_shared_secret = _string(webhook_shared_secret)
    if normalized_shared_secret:
        provided_secret = _pick(
            _header_value(headers, "X-Webhook-Secret", "X-Novofon-Secret"),
            query_secret,
        )
        if not provided_secret or not hmac.compare_digest(_string(provided_secret), normalized_shared_secret):
            return "invalid_secret"

    normalized_api_secret = _string(api_secret)
    if normalized_api_secret:
        provided_signature = extract_novofon_webhook_signature(headers)
        if not provided_signature:
            return "missing_signature"
        if not build_novofon_webhook_signature(payload if isinstance(payload, dict) else {}, secret=normalized_api_secret):
            return "unsupported_signature_payload"
        if not verify_novofon_webhook_signature(
            payload if isinstance(payload, dict) else {},
            provided_signature=provided_signature,
            secret=normalized_api_secret,
        ):
            return "invalid_signature"

    return ""
