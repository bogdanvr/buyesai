from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class IntegrationSecretError(ValueError):
    pass


def _secret_source() -> str:
    return str(getattr(settings, "INTEGRATIONS_SECRET_KEY", "") or "").strip()


def is_secret_encryption_configured() -> bool:
    return bool(_secret_source())


def _fernet() -> Fernet:
    raw_secret = _secret_source()
    if not raw_secret:
        raise IntegrationSecretError("Не задан INTEGRATIONS_SECRET_KEY.")
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return _fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    try:
        return _fernet().decrypt(normalized.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise IntegrationSecretError("Не удалось расшифровать секрет интеграции.") from exc
