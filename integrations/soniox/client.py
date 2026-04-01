from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class SonioxClientError(Exception):
    pass


class SonioxClient:
    DEFAULT_TIMEOUT = 30

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, model_id: str | None = None):
        self.api_key = str(api_key or settings.SONIOX_API_KEY or "").strip()
        self.base_url = str(base_url or settings.SONIOX_API_BASE_URL or "").strip().rstrip("/")
        self.model_id = str(model_id or settings.SONIOX_MODEL_ID or "").strip()
        if not self.api_key:
            raise SonioxClientError("Не задан SONIOX_API_KEY.")
        if not self.base_url:
            raise SonioxClientError("Не задан SONIOX_API_BASE_URL.")
        if not self.model_id:
            raise SonioxClientError("Не задан SONIOX_MODEL_ID.")

    def _request(self, method: str, path: str, *, payload: dict | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            logger.warning("Soniox API request failed. method=%s url=%s error=%s", method, url, error)
            raise SonioxClientError(str(error)) from error

        try:
            response_payload = response.json()
        except ValueError as error:
            raise SonioxClientError("Soniox вернул не-JSON ответ.") from error

        if isinstance(response_payload, dict) and response_payload.get("error"):
            error_payload = response_payload.get("error")
            if isinstance(error_payload, dict):
                message = str(error_payload.get("message") or error_payload.get("code") or "Soniox вернул ошибку API.").strip()
            else:
                message = str(error_payload).strip() or "Soniox вернул ошибку API."
            raise SonioxClientError(message)
        return response_payload if isinstance(response_payload, dict) else {}

    def create_transcription(
        self,
        *,
        audio_url: str,
        webhook_url: str = "",
        webhook_secret: str = "",
        client_reference_id: str = "",
        language_hints: list[str] | None = None,
        language_hints_strict: bool | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "audio_url": audio_url,
        }
        normalized_language_hints = [
            str(item or "").strip()
            for item in (language_hints or [])
            if str(item or "").strip()
        ]
        if normalized_language_hints:
            payload["language_hints"] = normalized_language_hints
            if language_hints_strict is not None:
                payload["language_hints_strict"] = bool(language_hints_strict)
        if client_reference_id:
            payload["client_reference_id"] = client_reference_id
        if webhook_url:
            webhook_payload: dict[str, Any] = {"url": webhook_url}
            if webhook_secret:
                webhook_payload["headers"] = {"X-Soniox-Webhook-Secret": webhook_secret}
            payload["webhook"] = webhook_payload
        return self._request("POST", "/transcriptions", payload=payload)

    def get_transcription(self, transcription_id: str) -> dict:
        return self._request("GET", f"/transcriptions/{transcription_id}")

    def get_transcript(self, transcription_id: str) -> dict:
        return self._request("GET", f"/transcriptions/{transcription_id}/transcript")
