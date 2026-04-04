from __future__ import annotations

from dataclasses import dataclass
import logging

from django.conf import settings

from integrations.models import LlmApiStyle, LlmProviderAccount
from integrations.services.secrets import IntegrationSecretError


logger = logging.getLogger(__name__)


@dataclass
class LlmRouteTarget:
    source: str
    label: str
    base_url: str
    api_key: str
    model: str
    organization: str = ""
    project: str = ""
    provider_account_id: int | None = None


def _build_target_from_provider(provider: LlmProviderAccount) -> LlmRouteTarget | None:
    try:
        api_key = provider.get_api_key()
    except IntegrationSecretError as exc:
        logger.warning("Failed to decrypt LLM provider id=%s: %s", provider.pk, exc)
        return None
    base_url = str(provider.base_url or "").strip()
    model = str(provider.model or "").strip()
    if not (base_url and model and api_key):
        return None
    return LlmRouteTarget(
        source="provider_account",
        label=str(provider.name or provider.get_provider_display() or f"provider-{provider.pk}").strip(),
        base_url=base_url,
        api_key=api_key,
        model=model,
        organization=str(provider.organization or "").strip(),
        project=str(provider.project or "").strip(),
        provider_account_id=provider.pk,
    )


def resolve_touch_analysis_llm_target() -> LlmRouteTarget | None:
    providers = LlmProviderAccount.objects.filter(
        is_active=True,
        use_for_touch_analysis=True,
        api_style=LlmApiStyle.OPENAI_COMPATIBLE,
    ).order_by("priority", "id")
    for provider in providers:
        target = _build_target_from_provider(provider)
        if target is not None:
            return target

    api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    base_url = str(getattr(settings, "OPENAI_API_BASE_URL", "") or "https://api.openai.com/v1").strip()
    model = str(getattr(settings, "OPENAI_MODEL", "") or "gpt-4o-mini").strip()
    if not (api_key and base_url and model):
        return None
    return LlmRouteTarget(
        source="settings",
        label="Глобальные настройки OpenAI",
        base_url=base_url,
        api_key=api_key,
        model=model,
        organization=str(getattr(settings, "OPENAI_ORG", "") or "").strip(),
        project=str(getattr(settings, "OPENAI_PROJECT", "") or "").strip(),
        provider_account_id=None,
    )
