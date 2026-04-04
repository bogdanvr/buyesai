from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re

from django.db import transaction
from django.utils import timezone
from requests import RequestException
import requests

from crm.models import AutomationDraft, AutomationRule, CommunicationChannel, Touch, TouchResult
from crm.models.automation import AutomationDraftKind, AutomationDraftStatus, AutomationTouchpointMode, AutomationUiMode, AutomationUiPriority
from crm.models.touch import TouchDirection, normalize_touch_channel_code
from integrations.services.llm_router import resolve_touch_analysis_llm_target


logger = logging.getLogger(__name__)

AI_TOUCH_ANALYSIS_EVENT_TYPE = "ai_touch_analysis_ready"
DEFAULT_CALL_CHANNEL_NAME = "Телефон"
MAX_ANALYSIS_TEXT_LENGTH = 12000
MIN_ANALYSIS_TEXT_LENGTH = 20


@dataclass
class TouchAiSuggestion:
    summary: str
    touch_result_code: str = ""
    touch_result_name: str = ""
    next_step: str = ""
    manager_note: str = ""
    confidence: str = ""


def _normalize_text(value: str, *, limit: int = MAX_ANALYSIS_TEXT_LENGTH) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _preview_text(value: str, *, limit: int = 240) -> str:
    text = _normalize_text(value, limit=MAX_ANALYSIS_TEXT_LENGTH)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _strip_json_fence(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


class TouchAiAnalysisService:
    @staticmethod
    def is_enabled() -> bool:
        return resolve_touch_analysis_llm_target() is not None

    @staticmethod
    def _api_url(base_url: str) -> str:
        base_url = str(base_url or "").strip().rstrip("/")
        return f"{base_url}/chat/completions"

    @staticmethod
    def _headers(*, api_key: str, organization: str = "", project: str = "") -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if organization:
            headers["OpenAI-Organization"] = organization
        if project:
            headers["OpenAI-Project"] = project
        return headers

    @staticmethod
    def _analysis_rule() -> AutomationRule:
        rule, created = AutomationRule.objects.get_or_create(
            event_type=AI_TOUCH_ANALYSIS_EVENT_TYPE,
            defaults={
                "ui_mode": AutomationUiMode.DRAFT_TOUCH,
                "ui_priority": AutomationUiPriority.HIGH,
                "write_timeline": False,
                "show_in_summary": True,
                "show_in_attention_queue": False,
                "merge_key": "ai_touch",
                "auto_open_panel": False,
                "create_message": False,
                "create_touchpoint_mode": AutomationTouchpointMode.DRAFT,
                "require_manager_confirmation": True,
                "allow_auto_create_task": False,
                "is_active": True,
                "sort_order": 5,
            },
        )
        if created:
            return rule

        update_fields: list[str] = []
        if str(rule.ui_mode or "") != AutomationUiMode.DRAFT_TOUCH:
            rule.ui_mode = AutomationUiMode.DRAFT_TOUCH
            update_fields.append("ui_mode")
        if str(rule.ui_priority or "") != AutomationUiPriority.HIGH:
            rule.ui_priority = AutomationUiPriority.HIGH
            update_fields.append("ui_priority")
        if bool(rule.require_manager_confirmation) is not True:
            rule.require_manager_confirmation = True
            update_fields.append("require_manager_confirmation")
        if str(rule.create_touchpoint_mode or "") != AutomationTouchpointMode.DRAFT:
            rule.create_touchpoint_mode = AutomationTouchpointMode.DRAFT
            update_fields.append("create_touchpoint_mode")
        if bool(rule.is_active) is not True:
            rule.is_active = True
            update_fields.append("is_active")
        if update_fields:
            rule.save(update_fields=[*update_fields, "updated_at"] if hasattr(rule, "updated_at") else update_fields)
        return rule

    @staticmethod
    def _touch_results_for_channel(channel: CommunicationChannel | None) -> list[TouchResult]:
        channel_code = normalize_touch_channel_code(getattr(channel, "name", ""))
        results = list(TouchResult.objects.filter(is_active=True).order_by("sort_order", "name"))
        if not channel_code:
            return results
        filtered = [
            item for item in results
            if not item.allowed_touch_types or channel_code in set(item.allowed_touch_types or [])
        ]
        return filtered or results

    @staticmethod
    def _request_suggestion(
        *,
        raw_text: str,
        channel_label: str,
        direction_label: str,
        candidate_results: list[TouchResult],
    ) -> TouchAiSuggestion | None:
        target = resolve_touch_analysis_llm_target()
        if target is None:
            return None

        candidates_payload = [
            {
                "code": str(item.code or "").strip(),
                "name": str(item.name or "").strip(),
                "group": str(item.group or "").strip(),
                "result_class": str(item.result_class or "").strip(),
            }
            for item in candidate_results
        ]
        prompt = (
            "Ты анализируешь текст клиентского касания для CRM. "
            "Верни только JSON без markdown. "
            "Нужно кратко и делово суммаризировать смысл текста, при возможности выбрать наиболее подходящий "
            "результат касания из списка и предложить следующий шаг. "
            "Если точного результата нет, оставь touch_result_code и touch_result_name пустыми. "
            "Не выдумывай факты, которых нет в тексте.\n"
            f"Канал: {channel_label}\n"
            f"Направление: {direction_label}\n"
            "Формат ответа:\n"
            "{"
            "\"summary\":\"...\","
            "\"touch_result_code\":\"...\","
            "\"touch_result_name\":\"...\","
            "\"next_step\":\"...\","
            "\"manager_note\":\"...\","
            "\"confidence\":\"low|medium|high\""
            "}\n"
            f"Доступные результаты касания: {json.dumps(candidates_payload, ensure_ascii=False)}"
        )
        body = {
            "model": target.model,
            "messages": [
                {"role": "developer", "content": prompt},
                {"role": "user", "content": raw_text},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        }
        try:
            response = requests.post(
                TouchAiAnalysisService._api_url(target.base_url),
                headers=TouchAiAnalysisService._headers(
                    api_key=target.api_key,
                    organization=target.organization,
                    project=target.project,
                ),
                json=body,
                timeout=40,
            )
            response.raise_for_status()
            payload = response.json()
        except (RequestException, ValueError) as exc:
            logger.warning("AI touch analysis request failed: %s", exc)
            return None

        content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        if not isinstance(content, str) or not content.strip():
            logger.warning("AI touch analysis returned empty content")
            return None

        cleaned_content = _strip_json_fence(content)
        try:
            parsed = json.loads(cleaned_content)
        except ValueError:
            logger.warning("AI touch analysis returned invalid JSON: %s", cleaned_content[:500])
            return None
        if not isinstance(parsed, dict):
            return None

        return TouchAiSuggestion(
            summary=_normalize_text(str(parsed.get("summary") or ""), limit=500),
            touch_result_code=str(parsed.get("touch_result_code") or "").strip(),
            touch_result_name=str(parsed.get("touch_result_name") or "").strip(),
            next_step=_normalize_text(str(parsed.get("next_step") or ""), limit=500),
            manager_note=_normalize_text(str(parsed.get("manager_note") or ""), limit=500),
            confidence=str(parsed.get("confidence") or "").strip().lower(),
        )

    @staticmethod
    def _resolve_touch_result(
        *,
        suggestion: TouchAiSuggestion,
        candidate_results: list[TouchResult],
    ) -> TouchResult | None:
        normalized_code = str(suggestion.touch_result_code or "").strip().lower()
        normalized_name = str(suggestion.touch_result_name or "").strip().lower()
        for item in candidate_results:
            if normalized_code and str(item.code or "").strip().lower() == normalized_code:
                return item
        for item in candidate_results:
            if normalized_name and str(item.name or "").strip().lower() == normalized_name:
                return item
        return None

    @staticmethod
    @transaction.atomic
    def _upsert_touch_draft(
        *,
        touch: Touch,
        suggestion: TouchAiSuggestion,
        analysis_label: str,
    ) -> AutomationDraft | None:
        if not suggestion.summary:
            return None
        rule = TouchAiAnalysisService._analysis_rule()
        acted_queryset = AutomationDraft.objects.filter(
            source_touch=touch,
            automation_rule=rule,
            draft_kind=AutomationDraftKind.TOUCH,
        ).exclude(status=AutomationDraftStatus.PENDING)
        if acted_queryset.exists():
            return None

        candidate_results = TouchAiAnalysisService._touch_results_for_channel(getattr(touch, "channel", None))
        touch_result = TouchAiAnalysisService._resolve_touch_result(
            suggestion=suggestion,
            candidate_results=candidate_results,
        )
        defaults = {
            "source_event_type": AI_TOUCH_ANALYSIS_EVENT_TYPE,
            "title": f"Автоматическое касание: {analysis_label}",
            "summary": suggestion.summary.strip(),
            "touch_result": touch_result,
            "proposed_channel": touch.channel,
            "proposed_direction": str(touch.direction or "").strip(),
            "proposed_next_step": str(suggestion.next_step or "").strip(),
            "proposed_next_step_at": None,
            "owner": touch.owner,
            "lead": touch.lead,
            "deal": touch.deal,
            "client": touch.client,
            "contact": touch.contact,
            "task": touch.task,
        }
        draft = AutomationDraft.objects.filter(
            source_touch=touch,
            automation_rule=rule,
            draft_kind=AutomationDraftKind.TOUCH,
            status=AutomationDraftStatus.PENDING,
        ).first()
        if draft is None:
            return AutomationDraft.objects.create(
                automation_rule=rule,
                source_touch=touch,
                draft_kind=AutomationDraftKind.TOUCH,
                status=AutomationDraftStatus.PENDING,
                **defaults,
            )
        for field_name, value in defaults.items():
            setattr(draft, field_name, value)
        draft.save()
        return draft

    @staticmethod
    def analyze_touch_text_if_needed(
        *,
        touch: Touch | None,
        raw_text: str,
        analysis_label: str,
    ) -> AutomationDraft | None:
        if touch is None:
            return None
        normalized_text = _normalize_text(raw_text)
        if len(normalized_text) < MIN_ANALYSIS_TEXT_LENGTH:
            return None
        candidate_results = TouchAiAnalysisService._touch_results_for_channel(getattr(touch, "channel", None))
        channel_label = str(getattr(getattr(touch, "channel", None), "name", "") or analysis_label).strip() or analysis_label
        direction_label = TouchDirection.INCOMING.label if str(touch.direction or "") == TouchDirection.INCOMING else TouchDirection.OUTGOING.label
        suggestion = TouchAiAnalysisService._request_suggestion(
            raw_text=normalized_text,
            channel_label=channel_label,
            direction_label=direction_label,
            candidate_results=candidate_results,
        )
        if suggestion is None:
            return None
        return TouchAiAnalysisService._upsert_touch_draft(
            touch=Touch.objects.select_related("channel", "owner", "lead", "deal", "client", "contact", "task").get(pk=touch.pk),
            suggestion=suggestion,
            analysis_label=analysis_label,
        )

    @staticmethod
    def analyze_message_touch_if_needed(*, message, touch: Touch | None = None) -> AutomationDraft | None:
        if message is None:
            return None
        if str(getattr(message, "direction", "") or "").strip() != "incoming":
            return None
        resolved_touch = touch or getattr(message, "touch", None)
        body_text = str(getattr(message, "body_text", "") or "").strip()
        subject = str(getattr(message, "subject", "") or "").strip()
        raw_text = body_text or subject
        if subject and body_text and subject.lower() not in body_text.lower():
            raw_text = f"Тема: {subject}\n\n{body_text}"
        channel = str(getattr(message, "channel", "") or "").strip().lower()
        analysis_label = "входящее сообщение"
        if channel == "email":
            analysis_label = "входящее письмо"
        elif channel == "telegram":
            analysis_label = "входящее сообщение Telegram"
        return TouchAiAnalysisService.analyze_touch_text_if_needed(
            touch=resolved_touch,
            raw_text=raw_text,
            analysis_label=analysis_label,
        )

    @staticmethod
    @transaction.atomic
    def ensure_phone_call_touch(call) -> Touch | None:
        if call is None:
            return None
        call = call.__class__.objects.select_related("touch", "responsible_user", "crm_user", "lead", "deal", "company", "contact").get(pk=call.pk)
        if getattr(call, "touch_id", None):
            return call.touch
        channel, _ = CommunicationChannel.objects.get_or_create(
            name=DEFAULT_CALL_CHANNEL_NAME,
            defaults={"is_active": True},
        )
        touch = Touch.objects.create(
            happened_at=call.ended_at or call.answered_at or call.started_at or timezone.now(),
            channel=channel,
            direction=TouchDirection.INCOMING if str(call.direction or "").strip().lower() == "inbound" else TouchDirection.OUTGOING,
            summary=_preview_text(call.transcription_text or "Телефонный разговор"),
            owner=call.responsible_user or call.crm_user,
            lead=call.lead,
            deal=call.deal,
            client=call.company,
            contact=call.contact,
        )
        call.touch = touch
        call.save(update_fields=["touch", "updated_at"])
        return touch

    @staticmethod
    def analyze_phone_call_if_needed(call) -> AutomationDraft | None:
        if call is None:
            return None
        transcript = str(getattr(call, "transcription_text", "") or "").strip()
        if len(_normalize_text(transcript)) < MIN_ANALYSIS_TEXT_LENGTH:
            return None
        touch = TouchAiAnalysisService.ensure_phone_call_touch(call)
        return TouchAiAnalysisService.analyze_touch_text_if_needed(
            touch=touch,
            raw_text=transcript,
            analysis_label="телефонный разговор",
        )
