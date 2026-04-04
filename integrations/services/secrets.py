from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class IntegrationSecretError(ValueError):
    pass


def _fernet_from_secret(raw_secret: str) -> Fernet:
    normalized = str(raw_secret or "").strip()
    if not normalized:
        raise IntegrationSecretError("Не задан секрет шифрования интеграций.")
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _secret_source() -> str:
    return str(getattr(settings, "INTEGRATIONS_SECRET_KEY", "") or "").strip()


def is_secret_encryption_configured() -> bool:
    return bool(_secret_source())


def _fernet() -> Fernet:
    if not _secret_source():
        raise IntegrationSecretError("Не задан INTEGRATIONS_SECRET_KEY.")
    return _fernet_from_secret(_secret_source())


def encrypt_secret_with_key(value: str, secret_key: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return _fernet_from_secret(secret_key).encrypt(normalized.encode("utf-8")).decode("utf-8")


def decrypt_secret_with_key(value: str, secret_key: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    try:
        return _fernet_from_secret(secret_key).decrypt(normalized.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise IntegrationSecretError("Не удалось расшифровать секрет интеграции.") from exc


def encrypt_secret(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return _fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return decrypt_secret_with_key(value, _secret_source())
