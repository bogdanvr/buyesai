from __future__ import annotations

import logging

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from integrations.models import PhoneCall, PhoneCallStatus, PhoneCallTranscriptionStatus
from integrations.soniox.client import SonioxClient, SonioxClientError


logger = logging.getLogger(__name__)

SONIOX_WEBHOOK_SECRET_HEADER = "X-Soniox-Webhook-Secret"


def _normalize_transcription_status(raw_status: str) -> str:
    normalized = str(raw_status or "").strip().lower()
    if normalized in {"queued", "pending"}:
        return PhoneCallTranscriptionStatus.QUEUED
    if normalized in {"transcribing", "processing", "in_progress", "running"}:
        return PhoneCallTranscriptionStatus.PROCESSING
    if normalized in {"completed", "done", "succeeded", "success"}:
        return PhoneCallTranscriptionStatus.COMPLETED
    if normalized in {"failed", "error", "canceled", "cancelled"}:
        return PhoneCallTranscriptionStatus.FAILED
    return PhoneCallTranscriptionStatus.PROCESSING if normalized else PhoneCallTranscriptionStatus.NOT_REQUESTED


def _build_webhook_url() -> str:
    base_url = str(getattr(settings, "CRM_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    if not base_url:
        return ""
    return f"{base_url}{reverse('integrations-soniox-webhook')}"


def _language_hints() -> list[str]:
    return [
        str(item or "").strip()
        for item in (getattr(settings, "SONIOX_LANGUAGE_HINTS", None) or ["ru"])
        if str(item or "").strip()
    ]


def _get_client() -> SonioxClient:
    return SonioxClient()


def _is_enabled() -> bool:
    return bool(str(getattr(settings, "SONIOX_API_KEY", "") or "").strip())


def _extract_transcription_id(payload: dict) -> str:
    transcription = payload.get("transcription") if isinstance(payload.get("transcription"), dict) else {}
    candidates = [
        payload.get("id"),
        payload.get("transcription_id"),
        transcription.get("id"),
        payload.get("object_id"),
    ]
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    data_payload = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    normalized = str(data_payload.get("id") or data_payload.get("transcription_id") or "").strip()
    return normalized


def _extract_transcription_status(payload: dict) -> str:
    transcription = payload.get("transcription") if isinstance(payload.get("transcription"), dict) else {}
    data_payload = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    candidates = [
        payload.get("status"),
        transcription.get("status"),
        data_payload.get("status"),
        payload.get("event"),
        payload.get("type"),
    ]
    for candidate in candidates:
        normalized = _normalize_transcription_status(candidate)
        if normalized != PhoneCallTranscriptionStatus.NOT_REQUESTED:
            return normalized
    return PhoneCallTranscriptionStatus.NOT_REQUESTED


def _extract_transcription_error(payload: dict) -> str:
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        return str(error_payload.get("message") or error_payload.get("code") or "").strip()
    return str(error_payload or payload.get("message") or "").strip()


def _extract_transcript_text(payload: dict) -> str:
    text = payload.get("text")
    if isinstance(text, str):
        return text.strip()
    transcript = payload.get("transcript")
    if isinstance(transcript, str):
        return transcript.strip()
    if isinstance(transcript, dict):
        nested_text = transcript.get("text")
        if isinstance(nested_text, str):
            return nested_text.strip()
    tokens = payload.get("tokens")
    if isinstance(tokens, list):
        parts = [str((item or {}).get("text") or "").strip() for item in tokens if isinstance(item, dict)]
        return " ".join(part for part in parts if part).strip()
    return ""


def _save_transcription_state(call: PhoneCall, *, save_fields: list[str]) -> None:
    if "updated_at" not in save_fields:
        save_fields.append("updated_at")
    call.save(update_fields=save_fields)


def refresh_phone_call_transcription(call: PhoneCall) -> dict:
    if not _is_enabled():
        return {"ok": False, "skipped": True, "reason": "soniox_disabled"}
    transcription_id = str(call.transcription_external_id or "").strip()
    if not transcription_id:
        return {"ok": False, "skipped": True, "reason": "transcription_not_requested"}

    client = _get_client()
    payload = client.get_transcription(transcription_id)
    normalized_status = _extract_transcription_status(payload)
    call.transcription_status = normalized_status
    call.transcription_error = _extract_transcription_error(payload)
    if normalized_status == PhoneCallTranscriptionStatus.COMPLETED:
        transcript_payload = client.get_transcript(transcription_id)
        call.transcription_text = _extract_transcript_text(transcript_payload)
        call.transcription_error = ""
        call.transcription_completed_at = timezone.now()
        _save_transcription_state(
            call,
            save_fields=[
                "transcription_status",
                "transcription_error",
                "transcription_text",
                "transcription_completed_at",
            ],
        )
        return {"ok": True, "status": call.transcription_status, "completed": True}
    if normalized_status == PhoneCallTranscriptionStatus.FAILED:
        call.transcription_completed_at = timezone.now()
    _save_transcription_state(
        call,
        save_fields=[
            "transcription_status",
            "transcription_error",
            "transcription_completed_at",
        ] if normalized_status == PhoneCallTranscriptionStatus.FAILED else [
            "transcription_status",
            "transcription_error",
        ],
    )
    return {"ok": True, "status": call.transcription_status, "completed": False}


def submit_phone_call_transcription_if_needed(call: PhoneCall) -> dict:
    if not _is_enabled():
        return {"ok": False, "skipped": True, "reason": "soniox_disabled"}
    recording_url = str(call.recording_url or "").strip()
    if not recording_url:
        return {"ok": False, "skipped": True, "reason": "recording_missing"}
    if (
        call.transcription_status == PhoneCallTranscriptionStatus.COMPLETED
        and call.transcription_recording_url == recording_url
        and call.transcription_text
    ):
        return {"ok": True, "skipped": True, "reason": "already_completed", "status": call.transcription_status}
    if (
        call.transcription_recording_url == recording_url
        and call.transcription_external_id
        and call.transcription_status in {PhoneCallTranscriptionStatus.QUEUED, PhoneCallTranscriptionStatus.PROCESSING}
    ):
        return {"ok": True, "skipped": True, "reason": "already_requested", "status": call.transcription_status}

    webhook_url = _build_webhook_url()
    webhook_secret = str(getattr(settings, "SONIOX_WEBHOOK_SECRET", "") or "").strip()
    now = timezone.now()
    client = _get_client()
    payload = client.create_transcription(
        audio_url=recording_url,
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        client_reference_id=f"phone_call:{call.pk}:{call.external_call_id}",
        language_hints=_language_hints(),
        language_hints_strict=bool(getattr(settings, "SONIOX_LANGUAGE_HINTS_STRICT", True)),
    )
    transcription_id = _extract_transcription_id(payload)
    if not transcription_id:
        raise SonioxClientError("Soniox не вернул ID транскрибации.")
    call.transcription_external_id = transcription_id
    call.transcription_recording_url = recording_url
    call.transcription_requested_at = now
    call.transcription_completed_at = None
    call.transcription_text = ""
    call.transcription_error = ""
    call.transcription_status = _extract_transcription_status(payload)
    if call.transcription_status == PhoneCallTranscriptionStatus.NOT_REQUESTED:
        call.transcription_status = PhoneCallTranscriptionStatus.QUEUED
    _save_transcription_state(
        call,
        save_fields=[
            "transcription_external_id",
            "transcription_recording_url",
            "transcription_requested_at",
            "transcription_completed_at",
            "transcription_text",
            "transcription_error",
            "transcription_status",
        ],
    )
    if call.transcription_status == PhoneCallTranscriptionStatus.COMPLETED:
        return refresh_phone_call_transcription(call)
    return {"ok": True, "submitted": True, "status": call.transcription_status, "transcription_id": transcription_id}


def process_soniox_transcription_webhook(*, payload: dict, headers: dict | None = None) -> dict:
    headers = headers or {}
    expected_secret = str(getattr(settings, "SONIOX_WEBHOOK_SECRET", "") or "").strip()
    header_secret = str(headers.get(SONIOX_WEBHOOK_SECRET_HEADER) or headers.get(SONIOX_WEBHOOK_SECRET_HEADER.lower()) or "").strip()
    if expected_secret and header_secret != expected_secret:
        raise ValueError("invalid_webhook_secret")

    transcription_id = _extract_transcription_id(payload)
    if not transcription_id:
        raise ValueError("missing_transcription_id")
    call = PhoneCall.objects.filter(transcription_external_id=transcription_id).first()
    if call is None:
        raise ValueError("phone_call_not_found")
    return refresh_phone_call_transcription(call)
