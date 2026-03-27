from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests

from integrations.models import TelephonyProviderAccount


logger = logging.getLogger(__name__)


class NovofonClientError(Exception):
    pass


class NovofonClient:
    DEFAULT_TIMEOUT = 10

    def __init__(self, account: TelephonyProviderAccount):
        self.account = account
        self.base_url = str(account.api_base_url or "").strip().rstrip("/") + "/"

    def _endpoint(self, setting_key: str, default_path: str) -> str:
        configured = str((self.account.settings_json or {}).get(setting_key) or "").strip()
        path = configured or default_path
        return urljoin(self.base_url, path.lstrip("/"))

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.account.api_key:
            headers["X-API-Key"] = self.account.api_key
        if self.account.api_secret:
            headers["X-API-Secret"] = self.account.api_secret
        return headers

    def _request(self, method: str, *, url: str, json_body: dict | None = None, params: dict | None = None) -> dict:
        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_body,
                params=params,
                headers=self._headers(),
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            logger.warning("Novofon API request failed. method=%s url=%s error=%s", method, url, error)
            raise NovofonClientError(str(error)) from error

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise NovofonClientError("Novofon вернул не-JSON ответ.") from error

    def ping(self) -> dict:
        return self._request("GET", url=self._endpoint("healthcheck_path", "/ping"))

    def list_employees(self) -> list[dict]:
        payload = self._request("GET", url=self._endpoint("employees_path", "/employees"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            records = payload.get("employees") or payload.get("results") or payload.get("data") or []
            return records if isinstance(records, list) else []
        return []

    def initiate_call(self, *, employee_id: str, extension: str, phone: str, comment: str = "", external_context: dict | None = None) -> dict:
        body = {
            "employee_id": employee_id,
            "extension": extension,
            "phone": phone,
            "comment": comment,
            "context": external_context or {},
        }
        return self._request("POST", url=self._endpoint("call_init_path", "/calls"), json_body=body)
