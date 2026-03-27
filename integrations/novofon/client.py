from __future__ import annotations

import logging
import uuid

import requests
from django.utils import timezone

from integrations.models import TelephonyProviderAccount
from integrations.novofon.selectors import normalize_phone


logger = logging.getLogger(__name__)


DEFAULT_DATA_API_BASE_URL = "https://dataapi-jsonrpc.novofon.ru/v2.0"
DEFAULT_CALL_API_BASE_URL = "https://callapi-jsonrpc.novofon.ru/v4.0"


class NovofonClientError(Exception):
    def __init__(self, message: str, *, mnemonic: str = "", field: str = ""):
        super().__init__(message)
        self.mnemonic = str(mnemonic or "").strip()
        self.field = str(field or "").strip()


class NovofonClient:
    DEFAULT_TIMEOUT = 10

    def __init__(self, account: TelephonyProviderAccount):
        self.account = account
        self.data_api_base_url = str(account.api_base_url or "").strip().rstrip("/") or DEFAULT_DATA_API_BASE_URL
        self.call_api_base_url = str((account.settings_json or {}).get("call_api_base_url") or "").strip().rstrip("/") or DEFAULT_CALL_API_BASE_URL

    def _access_token(self) -> str:
        token = str(self.account.api_key or "").strip()
        if not token:
            raise NovofonClientError("Не задан API key / access token Novofon.")
        return token

    def _request(self, url: str, *, method_name: str, params: dict | None = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": method_name,
            "params": params or {},
        }
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers={"Content-Type": "application/json; charset=UTF-8"},
                timeout=self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            logger.warning("Novofon API request failed. url=%s method=%s error=%s", url, method_name, error)
            raise NovofonClientError(str(error)) from error

        try:
            response_payload = response.json()
        except ValueError as error:
            raise NovofonClientError("Novofon вернул не-JSON ответ.") from error

        error_payload = response_payload.get("error") if isinstance(response_payload, dict) else None
        if isinstance(error_payload, dict):
            error_message = str(error_payload.get("message") or "Novofon вернул ошибку API.").strip()
            error_data = error_payload.get("data") if isinstance(error_payload.get("data"), dict) else {}
            mnemonic = str(error_data.get("mnemonic") or "").strip()
            field = str(error_data.get("field") or "").strip()
            if mnemonic:
                error_message = f"{error_message} [{mnemonic}]"
            raise NovofonClientError(error_message, mnemonic=mnemonic, field=field)

        result_payload = response_payload.get("result") if isinstance(response_payload, dict) else None
        return result_payload if isinstance(result_payload, dict) else {}

    def _data_api_request(self, method_name: str, params: dict | None = None) -> dict:
        merged_params = {
            "access_token": self._access_token(),
            **(params or {}),
        }
        return self._request(self.data_api_base_url, method_name=method_name, params=merged_params)

    def _call_api_request(self, method_name: str, params: dict | None = None) -> dict:
        merged_params = {
            "access_token": self._access_token(),
            **(params or {}),
        }
        return self._request(self.call_api_base_url, method_name=method_name, params=merged_params)

    def ping(self) -> dict:
        return self._data_api_request("get.account")

    def probe_call_api(self) -> dict:
        try:
            return self._call_api_request("release.call")
        except NovofonClientError as error:
            if error.mnemonic in {"required_parameter_missing", "required_parameter_missed", "invalid_parameter_value"}:
                return {"probe_error": str(error), "probe_mnemonic": error.mnemonic}
            raise

    def list_employees(self) -> list[dict]:
        payload = self._data_api_request(
            "get.employees",
            params={
                "limit": 1000,
                "offset": 0,
            },
        )
        records = payload.get("data") if isinstance(payload.get("data"), list) else []
        return records

    def list_virtual_numbers(self) -> list[dict]:
        payload = self._data_api_request(
            "get.virtual_numbers",
            params={
                "limit": 1000,
                "offset": 0,
            },
        )
        records = payload.get("data") if isinstance(payload.get("data"), list) else []
        return records

    def get_calls_report(
        self,
        *,
        date_from,
        date_till,
        limit: int = 500,
        offset: int = 0,
        include_ongoing_calls: bool = False,
        fields: list[str] | None = None,
    ) -> dict:
        params = {
            "date_from": timezone.localtime(date_from).strftime("%Y-%m-%d %H:%M:%S"),
            "date_till": timezone.localtime(date_till).strftime("%Y-%m-%d %H:%M:%S"),
            "limit": int(limit),
            "offset": int(offset),
            "include_ongoing_calls": bool(include_ongoing_calls),
        }
        if fields:
            params["fields"] = fields
        payload = self._data_api_request("get.calls_report", params=params)
        return {
            "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
            "data": payload.get("data") if isinstance(payload.get("data"), list) else [],
        }

    def _resolve_virtual_phone_number(self) -> str:
        allowed_numbers = [
            normalize_phone(item)
            for item in (self.account.allowed_virtual_numbers or [])
            if normalize_phone(item)
        ]
        virtual_numbers = self.list_virtual_numbers()
        active_virtual_numbers = [
            normalize_phone(item.get("virtual_phone_number") or "")
            for item in virtual_numbers
            if str(item.get("status") or "").strip().lower() == "active"
            and normalize_phone(item.get("virtual_phone_number") or "")
        ]
        if allowed_numbers:
            for allowed_number in allowed_numbers:
                if allowed_number in active_virtual_numbers:
                    return allowed_number
            raise NovofonClientError("Ни один из разрешенных виртуальных номеров не найден среди активных номеров Novofon.")
        if active_virtual_numbers:
            return active_virtual_numbers[0]
        raise NovofonClientError("В Novofon не найден активный виртуальный номер для исходящего звонка.")

    def initiate_call(self, *, employee_id: str, extension: str, phone: str, comment: str = "", external_context: dict | None = None) -> dict:
        normalized_phone = normalize_phone(phone)
        if not normalized_phone:
            raise NovofonClientError("Некорректный номер телефона для исходящего звонка.")

        virtual_phone_number = self._resolve_virtual_phone_number()
        employee_payload = {"id": employee_id}
        employee_phone_number = str(extension or "").strip()
        if employee_phone_number:
            employee_payload["phone_number"] = employee_phone_number

        params = {
            "first_call": "employee",
            "switch_at_once": True,
            "show_virtual_phone_number": False,
            "virtual_phone_number": virtual_phone_number,
            "contact": normalized_phone,
            "employee": employee_payload,
            "direction": "out",
        }
        external_id = str((external_context or {}).get("phone_call_id") or "").strip()
        if external_id:
            params["external_id"] = f"crm_phone_call_{external_id}"

        payload = self._call_api_request("start.employee_call", params=params)
        data_payload = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        return {
            **data_payload,
            "virtual_phone_number": virtual_phone_number,
            "comment": comment,
        }
