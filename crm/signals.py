import logging

from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from audit.services import log_model_event
from crm.models import Activity, AutomationDraft, AutomationMessageDraft, AutomationQueueItem, Client, ClientDocument, Deal, DealDocument, DealStage, Lead, Touch, TouchResult
from crm.models.activity import (
    ActivityType,
    TaskStatus,
    task_type_uses_communication_channel,
)
from crm.models.automation import (
    AutomationDraftKind,
    AutomationMessageDraftStatus,
    AutomationDraftStatus,
    AutomationQueueItemKind,
    AutomationQueueItemStatus,
    AutomationRule,
)
from crm.models.touch import DIRECT_TOUCH_EVENT_TYPES_BY_RESULT_CODE, TouchDirection, normalize_touch_channel_code, resolve_touch_event_type
from crm.services.automation import (
    infer_next_step_due_at,
    resolve_touch_automation_rule,
    should_auto_create_touch_follow_up_task,
    should_write_touch_timeline,
    upsert_touch_follow_up_task,
)
from crm.services.lead_services import convert_lead_to_deal


logger = logging.getLogger(__name__)

ACTIVE_TASK_STATUSES = {TaskStatus.TODO, TaskStatus.IN_PROGRESS}


def _extract_deal_failed_reason(deal: Deal | None) -> str:
    if deal is None:
        return ""
    metadata = getattr(deal, "metadata", {}) or {}
    return str(metadata.get("failed_reason", "") or "").strip()


def _format_structured_event_entry(
    *,
    result_text: str,
    happened_at=None,
    task_id: int | None = None,
    touch_id: int | None = None,
    deal_id: int | None = None,
    event_type: str | None = None,
    priority: str | None = None,
    extra_lines: list[str] | None = None,
) -> str:
    timestamp = timezone.localtime(happened_at or timezone.now()).strftime("%d.%m.%Y %H:%M")
    lines = [timestamp, f"Результат: {str(result_text or '').strip()}"]
    if event_type:
        lines.append(f"event_type: {event_type}")
    if priority:
        lines.append(f"priority: {priority}")
    if task_id:
        lines.append(f"task_id: {task_id}")
    if touch_id:
        lines.append(f"touch_id: {touch_id}")
    if deal_id:
        lines.append(f"deal_id: {deal_id}")
    if extra_lines:
        lines.extend([str(line or "").strip() for line in extra_lines if str(line or "").strip()])
    return "\n".join(lines)


def _prepend_event(existing: str, entry: str) -> str:
    current = str(existing or "").strip()
    return entry if not current else f"{entry}\n\n{current}"


def _replace_latest_touch_event(existing: str, touch_id: int, entry: str) -> str:
    current = str(existing or "").strip()
    if not current or not touch_id:
        return entry if not current else _prepend_event(current, entry)

    chunks = [chunk.strip() for chunk in current.split("\n\n") if chunk.strip()]
    target_touch_line = f"touch_id: {touch_id}"
    for index, chunk in enumerate(chunks):
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if target_touch_line in lines and "event_type: touch" in lines:
          chunks[index] = entry
          return "\n\n".join(chunks)
    return _prepend_event(current, entry)


def _prepend_note(existing: str, entry: str) -> str:
    current = str(existing or "").strip()
    return entry if not current else f"{entry}\n\n{current}"


def _actor_display_name(user) -> str:
    if user is None:
        return "Система"
    full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return str(full_name or getattr(user, "username", "") or "Система").strip()


def _format_company_note_entry(*, note_text: str, actor=None, deal_id: int | None = None, happened_at=None) -> str:
    timestamp = timezone.localtime(happened_at or timezone.now()).strftime("%d.%m.%Y")
    lines = [f"{timestamp} · Добавил: {_actor_display_name(actor)}"]
    if deal_id:
        lines.append(f"Сделка #{deal_id}")
    lines.append(str(note_text or "").strip())
    return "\n".join(lines)


def _append_client_event(client_id: int | None, entry: str) -> None:
    if not client_id:
        return
    client = Client.objects.filter(pk=client_id).only("id", "events").first()
    if client is None:
        return
    Client.objects.filter(pk=client.pk).update(events=_prepend_event(client.events, entry))


def _append_client_note(client_id: int | None, entry: str) -> None:
    if not client_id:
        return
    client = Client.objects.filter(pk=client_id).only("id", "notes").first()
    if client is None:
        return
    Client.objects.filter(pk=client.pk).update(notes=_prepend_note(client.notes, entry))


def _append_deal_event(deal_id: int | None, entry: str) -> None:
    if not deal_id:
        return
    deal = Deal.objects.filter(pk=deal_id).only("id", "events").first()
    if deal is None:
        return
    Deal.objects.filter(pk=deal.pk).update(events=_prepend_event(deal.events, entry))


def _append_lead_event(lead_id: int | None, entry: str) -> None:
    if not lead_id:
        return
    lead = Lead.objects.filter(pk=lead_id).only("id", "events").first()
    if lead is None:
        return
    Lead.objects.filter(pk=lead.pk).update(events=_prepend_event(lead.events, entry))


def _replace_touch_event_in_deal(deal_id: int | None, touch_id: int | None, entry: str) -> None:
    if not deal_id or not touch_id:
        return
    deal = Deal.objects.filter(pk=deal_id).only("id", "events").first()
    if deal is None:
        return
    Deal.objects.filter(pk=deal.pk).update(events=_replace_latest_touch_event(deal.events, touch_id, entry))


def _replace_touch_event_in_lead(lead_id: int | None, touch_id: int | None, entry: str) -> None:
    if not lead_id or not touch_id:
        return
    lead = Lead.objects.filter(pk=lead_id).only("id", "events").first()
    if lead is None:
        return
    Lead.objects.filter(pk=lead.pk).update(events=_replace_latest_touch_event(lead.events, touch_id, entry))


def _replace_touch_event_in_client(client_id: int | None, touch_id: int | None, entry: str) -> None:
    if not client_id or not touch_id:
        return
    client = Client.objects.filter(pk=client_id).only("id", "events").first()
    if client is None:
        return
    Client.objects.filter(pk=client.pk).update(events=_replace_latest_touch_event(client.events, touch_id, entry))


def _document_download_url(document) -> str:
    if isinstance(document, DealDocument):
        return reverse("deal-documents-download", kwargs={"pk": document.pk})
    if isinstance(document, ClientDocument):
        return reverse("client-documents-download", kwargs={"pk": document.pk})
    return ""


def _touch_result_label(instance: Touch) -> str:
    return str(getattr(getattr(instance, "result_option", None), "name", "") or "").strip()


def _touch_channel_label(instance: Touch) -> str:
    return str(getattr(getattr(instance, "channel", None), "name", "") or "").strip()


def _touch_direction_label(direction: str) -> str:
    return TouchDirection.OUTGOING.label if direction == TouchDirection.OUTGOING else TouchDirection.INCOMING.label


def _touch_title(instance: Touch) -> str:
    channel_label = _touch_channel_label(instance).strip().lower()
    direction_label = _touch_direction_label(instance.direction)
    if channel_label:
        return f"{direction_label} {channel_label}"
    return f"{direction_label} касание"


def _touch_automation_title(instance: Touch, rule: AutomationRule | None = None, *, prefer_next_step: bool = False) -> str:
    next_step_text = str(getattr(getattr(rule, "next_step_template", None), "name", "") or instance.next_step or "").strip()
    touch_result = _resolve_touch_result_from_outcome(rule, instance)
    result_label = str(getattr(touch_result, "name", "") or "").strip()
    result_code = str(getattr(touch_result, "code", "") or "").strip().lower()
    if prefer_next_step and next_step_text:
        return next_step_text
    if result_code in DIRECT_TOUCH_EVENT_TYPES_BY_RESULT_CODE and result_label:
        return result_label
    return _touch_title(instance)


def _resolve_touch_event_type(instance: Touch) -> str:
    return resolve_touch_event_type(
        channel_code=getattr(getattr(instance, "channel", None), "name", ""),
        direction=str(instance.direction or "").strip().lower(),
        result_code=str(getattr(getattr(instance, "result_option", None), "code", "") or "").strip().lower(),
    )


def _resolve_touch_result_from_outcome(rule: AutomationRule | None, instance: Touch) -> TouchResult | None:
    outcome = getattr(rule, "default_outcome", None)
    if outcome is None:
        return getattr(instance, "result_option", None)
    outcome_code = str(getattr(outcome, "code", "") or "").strip()
    outcome_name = str(getattr(outcome, "name", "") or "").strip()
    touch_result = None
    if outcome_code:
        touch_result = TouchResult.objects.filter(code=outcome_code).first()
    if touch_result is None and outcome_name:
        touch_result = TouchResult.objects.filter(name=outcome_name).first()
    return touch_result or getattr(instance, "result_option", None)


def _resolve_touch_client(instance: Touch):
    if instance.client_id:
        return instance.client
    if instance.deal_id and getattr(instance.deal, "client", None):
        return instance.deal.client
    if instance.lead_id and getattr(instance.lead, "client", None):
        return instance.lead.client
    if instance.contact_id and getattr(instance.contact, "client", None):
        return instance.contact.client
    return None


def _draft_defaults_from_touch(instance: Touch, rule: AutomationRule, draft_kind: str) -> dict:
    resolved_client = _resolve_touch_client(instance)
    next_step_text = str(getattr(getattr(rule, "next_step_template", None), "name", "") or instance.next_step or "").strip()
    touch_result = _resolve_touch_result_from_outcome(rule, instance)
    event_type = _resolve_touch_event_type(instance)
    proposed_next_step_at = infer_next_step_due_at(
        current_due_at=getattr(instance, "next_step_at", None),
        next_step_template=getattr(rule, "next_step_template", None),
        base_datetime=getattr(instance, "happened_at", None) or timezone.now(),
    )
    if draft_kind == AutomationDraftKind.NEXT_STEP:
        title = next_step_text or _touch_automation_title(instance, rule, prefer_next_step=True)
        summary = str(instance.summary or "").strip()
    else:
        title = _touch_automation_title(instance, rule)
        summary = str(instance.summary or getattr(touch_result, "name", "") or "").strip()
    return {
        "source_event_type": event_type,
        "title": title,
        "summary": summary,
        "outcome": getattr(rule, "default_outcome", None),
        "touch_result": touch_result,
        "next_step_template": getattr(rule, "next_step_template", None),
        "proposed_channel": getattr(instance, "channel", None),
        "proposed_direction": str(instance.direction or "").strip(),
        "proposed_next_step": next_step_text,
        "proposed_next_step_at": proposed_next_step_at,
        "owner": getattr(instance, "owner", None),
        "lead": getattr(instance, "lead", None),
        "deal": getattr(instance, "deal", None),
        "client": resolved_client,
        "contact": getattr(instance, "contact", None),
        "task": getattr(instance, "task", None),
    }


def _upsert_touch_automation_draft(instance: Touch, rule: AutomationRule, draft_kind: str) -> None:
    acted_queryset = AutomationDraft.objects.filter(
        source_touch=instance,
        automation_rule=rule,
        draft_kind=draft_kind,
    ).exclude(status=AutomationDraftStatus.PENDING)
    if acted_queryset.exists():
        return
    defaults = _draft_defaults_from_touch(instance, rule, draft_kind)
    draft = AutomationDraft.objects.filter(
        source_touch=instance,
        automation_rule=rule,
        draft_kind=draft_kind,
        status=AutomationDraftStatus.PENDING,
    ).first()
    if draft is None:
        AutomationDraft.objects.create(
            automation_rule=rule,
            source_touch=instance,
            draft_kind=draft_kind,
            status=AutomationDraftStatus.PENDING,
            **defaults,
        )
        return
    for field_name, value in defaults.items():
        setattr(draft, field_name, value)
    draft.save()


def _create_touch_automation_touch(instance: Touch, rule: AutomationRule) -> Touch | None:
    defaults = _draft_defaults_from_touch(instance, rule, AutomationDraftKind.TOUCH)
    happened_at = getattr(instance, "happened_at", None) or timezone.now()
    summary = str(defaults.get("summary") or defaults.get("title") or "").strip()
    auto_touch = Touch(
        happened_at=happened_at,
        channel=defaults.get("proposed_channel"),
        direction=str(defaults.get("proposed_direction") or instance.direction or TouchDirection.OUTGOING).strip() or TouchDirection.OUTGOING,
        result_option=defaults.get("touch_result"),
        summary=summary,
        next_step=str(defaults.get("proposed_next_step") or "").strip(),
        next_step_at=defaults.get("proposed_next_step_at"),
        owner=defaults.get("owner"),
        lead=defaults.get("lead"),
        deal=defaults.get("deal"),
        client=defaults.get("client"),
        contact=defaults.get("contact"),
        task=None,
    )
    # The auto-created touch should stay a normal CRM touch, but it must not
    # recursively trigger the same automation rule again.
    auto_touch._skip_touch_automation = True
    auto_touch.save()
    return auto_touch


def _queue_defaults_from_touch(instance: Touch, rule: AutomationRule, item_kind: str) -> dict:
    resolved_client = _resolve_touch_client(instance)
    next_step_text = str(getattr(getattr(rule, "next_step_template", None), "name", "") or instance.next_step or "").strip()
    touch_result = _resolve_touch_result_from_outcome(rule, instance)
    event_type = _resolve_touch_event_type(instance)
    proposed_next_step_at = infer_next_step_due_at(
        current_due_at=getattr(instance, "next_step_at", None),
        next_step_template=getattr(rule, "next_step_template", None),
        base_datetime=getattr(instance, "happened_at", None) or timezone.now(),
    )
    if item_kind == AutomationQueueItemKind.NEXT_STEP:
        title = next_step_text or _touch_automation_title(instance, rule, prefer_next_step=True)
        summary = str(instance.summary or "").strip()
        recommended_action = next_step_text
    else:
        title = _touch_automation_title(instance, rule)
        summary = str(instance.summary or getattr(touch_result, "name", "") or "").strip()
        recommended_action = next_step_text or str(getattr(getattr(rule, "next_step_template", None), "name", "") or "").strip()
    return {
        "source_event_type": event_type,
        "title": title,
        "summary": summary,
        "recommended_action": recommended_action,
        "outcome": getattr(rule, "default_outcome", None),
        "touch_result": touch_result,
        "next_step_template": getattr(rule, "next_step_template", None),
        "proposed_channel": getattr(instance, "channel", None),
        "proposed_direction": str(instance.direction or "").strip(),
        "proposed_next_step": next_step_text,
        "proposed_next_step_at": proposed_next_step_at,
        "owner": getattr(instance, "owner", None),
        "lead": getattr(instance, "lead", None),
        "deal": getattr(instance, "deal", None),
        "client": resolved_client,
        "contact": getattr(instance, "contact", None),
        "task": getattr(instance, "task", None),
    }


def _upsert_touch_automation_queue_item(instance: Touch, rule: AutomationRule, item_kind: str) -> None:
    acted_queryset = AutomationQueueItem.objects.filter(
        source_touch=instance,
        automation_rule=rule,
        item_kind=item_kind,
    ).exclude(status=AutomationQueueItemStatus.PENDING)
    if acted_queryset.exists():
        return
    defaults = _queue_defaults_from_touch(instance, rule, item_kind)
    item = AutomationQueueItem.objects.filter(
        source_touch=instance,
        automation_rule=rule,
        item_kind=item_kind,
        status=AutomationQueueItemStatus.PENDING,
    ).first()
    if item is None:
        AutomationQueueItem.objects.create(
            automation_rule=rule,
            source_touch=instance,
            item_kind=item_kind,
            status=AutomationQueueItemStatus.PENDING,
            **defaults,
        )
        return
    for field_name, value in defaults.items():
        setattr(item, field_name, value)
    item.save()


def _message_draft_defaults_from_touch(instance: Touch, rule: AutomationRule) -> dict:
    resolved_client = _resolve_touch_client(instance)
    channel = getattr(instance, "channel", None)
    event_type = _resolve_touch_event_type(instance)
    event_title = _touch_automation_title(instance, rule)
    result_label = _touch_result_label(instance)
    subject = str(getattr(getattr(rule, "next_step_template", None), "name", "") or result_label or event_title).strip()
    message_parts = [str(instance.summary or "").strip()]
    if result_label and result_label not in message_parts:
        message_parts.append(result_label)
    next_step_label = str(getattr(getattr(rule, "next_step_template", None), "name", "") or instance.next_step or "").strip()
    if next_step_label:
        message_parts.append(f"Следующий шаг: {next_step_label}")
    message_text = "\n".join(part for part in message_parts if part)
    return {
        "source_event_type": event_type,
        "title": f"Сообщение: {event_title}",
        "message_subject": subject,
        "message_text": message_text,
        "proposed_channel": channel,
        "owner": getattr(instance, "owner", None),
        "lead": getattr(instance, "lead", None),
        "deal": getattr(instance, "deal", None),
        "client": resolved_client,
        "contact": getattr(instance, "contact", None),
    }


def _upsert_touch_automation_message_draft(instance: Touch, rule: AutomationRule) -> None:
    acted_queryset = AutomationMessageDraft.objects.filter(
        source_touch=instance,
        automation_rule=rule,
    ).exclude(status=AutomationMessageDraftStatus.PENDING)
    if acted_queryset.exists():
        return
    defaults = _message_draft_defaults_from_touch(instance, rule)
    draft = AutomationMessageDraft.objects.filter(
        source_touch=instance,
        automation_rule=rule,
        status=AutomationMessageDraftStatus.PENDING,
    ).first()
    if draft is None:
        AutomationMessageDraft.objects.create(
            automation_rule=rule,
            source_touch=instance,
            status=AutomationMessageDraftStatus.PENDING,
            **defaults,
        )
        return
    for field_name, value in defaults.items():
        setattr(draft, field_name, value)
    draft.save()


def _dismiss_pending_touch_automation_artifacts(
    instance: Touch,
    *,
    rule: AutomationRule | None,
    allowed_draft_kinds: set[str] | None = None,
    allowed_queue_kinds: set[str] | None = None,
    allow_message_draft: bool = False,
) -> None:
    acted_at = timezone.now()

    draft_queryset = AutomationDraft.objects.filter(
        source_touch=instance,
        status=AutomationDraftStatus.PENDING,
    )
    if rule is not None and allowed_draft_kinds:
        draft_queryset = draft_queryset.exclude(
            automation_rule=rule,
            draft_kind__in=list(allowed_draft_kinds),
        )
    draft_queryset.update(
        status=AutomationDraftStatus.DISMISSED,
        acted_at=acted_at,
        updated_at=acted_at,
    )

    queue_queryset = AutomationQueueItem.objects.filter(
        source_touch=instance,
        status=AutomationQueueItemStatus.PENDING,
    )
    if rule is not None and allowed_queue_kinds:
        queue_queryset = queue_queryset.exclude(
            automation_rule=rule,
            item_kind__in=list(allowed_queue_kinds),
        )
    queue_queryset.update(
        status=AutomationQueueItemStatus.DISMISSED,
        acted_at=acted_at,
        updated_at=acted_at,
    )

    message_draft_queryset = AutomationMessageDraft.objects.filter(
        source_touch=instance,
        status=AutomationMessageDraftStatus.PENDING,
    )
    if rule is not None and allow_message_draft:
        message_draft_queryset = message_draft_queryset.exclude(automation_rule=rule)
    message_draft_queryset.update(
        status=AutomationMessageDraftStatus.DISMISSED,
        acted_at=acted_at,
        updated_at=acted_at,
    )


def _touch_document_event_lines(instance: Touch) -> list[str]:
    lines: list[str] = []
    for document in instance.client_documents.all():
        document_name = str(document.original_name or getattr(document.file, "name", "") or "").strip()
        if document_name:
            lines.append(f"document_name: {document_name}")
            lines.append(f"document_url: {_document_download_url(document)}")
    for document in instance.deal_documents.all():
        document_name = str(document.original_name or getattr(document.file, "name", "") or "").strip()
        if document_name:
            lines.append(f"document_name: {document_name}")
            lines.append(f"document_url: {_document_download_url(document)}")
    return lines


def _touch_communication_event_lines(instance: Touch) -> list[str]:
    message = getattr(instance, "communication_message", None)
    if message is None:
        return []
    lines: list[str] = []
    if getattr(message, "conversation_id", None):
        lines.append(f"conversation_id: {message.conversation_id}")
    if getattr(message, "id", None):
        lines.append(f"communication_message_id: {message.id}")
    if getattr(message, "channel", None):
        lines.append(f"communication_channel: {message.channel}")
    return lines


def _touch_event_extra_lines(instance: Touch, channel_label: str, result_label: str) -> list[str]:
    return [
        f"title: {_touch_title(instance)}",
        f"actor_name: {_actor_display_name(instance.owner)}",
        channel_label and f"channel_name: {channel_label}",
        f"direction_label: {_touch_direction_label(instance.direction)}",
        result_label and f"touch_result: {result_label}",
        instance.summary and f"summary: {instance.summary}",
        instance.next_step and f"next_step: {instance.next_step}",
        instance.next_step_at and f"next_step_at: {timezone.localtime(instance.next_step_at).isoformat()}",
        *_touch_communication_event_lines(instance),
        *_touch_document_event_lines(instance),
    ]


def _task_status_label(status: str) -> str:
    return TaskStatus(status).label if status in TaskStatus.values else str(status or "").strip()


def _task_related_client_ids(instance: Activity) -> list[int]:
    client_ids = []
    candidates = [
        instance.client_id,
        instance.deal.client_id if instance.deal_id and instance.deal else None,
        instance.lead.client_id if instance.lead_id and instance.lead else None,
    ]
    for client_id in candidates:
        if client_id and client_id not in client_ids:
            client_ids.append(client_id)
    return client_ids


def _resolve_task_completion_event_type(instance: Activity) -> str:
    if instance.type != ActivityType.TASK or instance.status != TaskStatus.DONE:
        return ""
    if not task_type_uses_communication_channel(getattr(instance, "task_type", None)):
        return "internal_task_completed"
    channel_code = normalize_touch_channel_code(getattr(getattr(instance, "communication_channel", None), "name", ""))
    if channel_code == "call":
        return "client_task_completed_call"
    if channel_code == "meeting":
        return "client_task_completed_meeting"
    return "client_task_completed_email"


def _resolve_auto_follow_up_due_at(instance: Activity):
    now = instance.completed_at or timezone.now()
    due_at = getattr(instance, "due_at", None)
    if due_at is None:
        return now
    return due_at if due_at >= now else now


@receiver(post_save, sender=Lead)
def lead_audit_signal(sender, instance: Lead, created, **kwargs):
    log_model_event(instance=instance, action="lead.created" if created else "lead.updated")


@receiver(pre_save, sender=Lead)
def lead_previous_state_signal(sender, instance: Lead, **kwargs):
    instance._previous_lead_state = None
    if not instance.pk:
        return
    instance._previous_lead_state = (
        Lead.objects.filter(pk=instance.pk)
        .select_related("status", "source", "assigned_to")
        .only(
            "title",
            "company",
            "status_id",
            "status__name",
            "source_id",
            "source__name",
            "assigned_to_id",
            "assigned_to__username",
            "assigned_to__first_name",
            "assigned_to__last_name",
            "expected_value",
        )
        .first()
    )


@receiver(post_save, sender=Lead)
def lead_system_events_signal(sender, instance: Lead, created, **kwargs):
    previous = getattr(instance, "_previous_lead_state", None)
    if created:
        entry = _format_structured_event_entry(
            result_text=f"Лид создан: {instance.title or instance.name or f'Лид #{instance.pk}'}",
            happened_at=instance.created_at,
            event_type="system",
            priority="low",
            extra_lines=["title: Системное событие"],
        )
        _append_lead_event(instance.pk, entry)
        return

    if previous is None:
        return

    changes: list[str] = []
    if str(previous.title or "").strip() != str(instance.title or "").strip():
        changes.append(f"Название лида изменено: {previous.title or 'Без названия'} -> {instance.title or 'Без названия'}")
    if str(previous.company or "").strip() != str(instance.company or "").strip():
        changes.append(f"Компания лида изменена: {previous.company or 'Не указана'} -> {instance.company or 'Не указана'}")
    if getattr(previous, "status_id", None) != getattr(instance, "status_id", None):
        previous_status = str(getattr(getattr(previous, "status", None), "name", "") or "Не выбран")
        current_status = str(getattr(getattr(instance, "status", None), "name", "") or "Не выбран")
        changes.append(f"Статус лида изменён: {previous_status} -> {current_status}")
    if getattr(previous, "source_id", None) != getattr(instance, "source_id", None):
        previous_source = str(getattr(getattr(previous, "source", None), "name", "") or "Не выбран")
        current_source = str(getattr(getattr(instance, "source", None), "name", "") or "Не выбран")
        changes.append(f"Источник лида изменён: {previous_source} -> {current_source}")
    if getattr(previous, "assigned_to_id", None) != getattr(instance, "assigned_to_id", None):
        changes.append(
            f"Ответственный изменён: {_actor_display_name(getattr(previous, 'assigned_to', None))} -> {_actor_display_name(getattr(instance, 'assigned_to', None))}"
        )
    if getattr(previous, "expected_value", None) != getattr(instance, "expected_value", None):
        changes.append(f"Ожидаемая сумма изменена: {previous.expected_value or 0} -> {instance.expected_value or 0}")

    for change_text in changes:
        entry = _format_structured_event_entry(
            result_text=change_text,
            event_type="system",
            priority="low",
            extra_lines=["title: Системное событие"],
        )
        _append_lead_event(instance.pk, entry)


def _resolve_converted_stage():
    active_stages = DealStage.objects.filter(is_active=True)

    preferred_codes = ("new", "open", "in_progress", "qualification")
    preferred_stage = (
        active_stages.filter(code__in=preferred_codes, is_final=False)
        .order_by("order", "id")
        .first()
    )
    if preferred_stage is not None:
        return preferred_stage

    return active_stages.filter(is_final=False).order_by("order", "id").first()


@receiver(post_save, sender=Lead)
def lead_auto_convert_signal(sender, instance: Lead, **kwargs):
    status = instance.status
    status_code = ((status.code if status else "") or "").strip().lower()
    if status_code != "converted":
        return
    if instance.deals.exists():
        return

    try:
        convert_lead_to_deal(
            lead=instance,
            stage=_resolve_converted_stage(),
            owner=instance.assigned_to,
        )
    except Exception:
        logger.exception("Failed to auto-create deal for converted lead_id=%s", instance.id)


@receiver(post_save, sender=Deal)
def deal_audit_signal(sender, instance: Deal, created, **kwargs):
    log_model_event(instance=instance, action="deal.created" if created else "deal.updated")


@receiver(post_save, sender=Activity)
def activity_audit_signal(sender, instance: Activity, created, **kwargs):
    log_model_event(instance=instance, action="activity.created" if created else "activity.updated")


@receiver(pre_save, sender=Activity)
def activity_task_deadline_state_signal(sender, instance: Activity, **kwargs):
    if instance.type != ActivityType.TASK:
        return

    instance._previous_activity_state = None
    if not instance.pk:
        if instance.status not in ACTIVE_TASK_STATUSES:
            instance.deadline_reminder_sent_at = None
            instance.deadline_reminder_acknowledged_at = None
            instance.deadline_reminder_email_escalated_at = None
        return

    previous = (
        Activity.objects.filter(pk=instance.pk)
        .select_related("deal", "lead")
        .only(
            "type",
            "subject",
            "due_at",
            "deadline_reminder_offset_minutes",
            "is_done",
            "status",
            "result",
            "save_company_note",
            "company_note",
            "client_id",
            "deal_id",
            "deal__client_id",
            "lead_id",
            "lead__client_id",
            "deadline_reminder_sent_at",
        )
        .first()
    )
    instance._previous_activity_state = previous

    if instance.status not in ACTIVE_TASK_STATUSES:
        instance.deadline_reminder_sent_at = None
        instance.deadline_reminder_acknowledged_at = None
        instance.deadline_reminder_email_escalated_at = None

    if previous is None or previous.type != ActivityType.TASK:
        return

    due_at_changed = previous.due_at != instance.due_at
    reminder_offset_changed = (
        previous.deadline_reminder_offset_minutes != instance.deadline_reminder_offset_minutes
    )
    reopened = previous.status not in ACTIVE_TASK_STATUSES and instance.status in ACTIVE_TASK_STATUSES
    if due_at_changed or reminder_offset_changed or reopened:
        instance.deadline_reminder_sent_at = None
        instance.deadline_reminder_acknowledged_at = None
        instance.deadline_reminder_email_escalated_at = None


@receiver(post_save, sender=Activity)
def activity_task_events_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != ActivityType.TASK:
        return

    if created:
        entry = _format_structured_event_entry(
            result_text=f"Создана задача: {instance.subject}",
            happened_at=instance.created_at,
            task_id=instance.pk,
            deal_id=instance.deal_id,
            event_type="task",
            priority="medium" if instance.status in ACTIVE_TASK_STATUSES else "low",
            extra_lines=[
                f"title: Задача: {instance.subject}",
                getattr(instance.task_type, "name", "") and f"task_type_name: {instance.task_type.name}",
                f"task_status_label: {_task_status_label(instance.status)}",
                instance.due_at and f"due_at: {timezone.localtime(instance.due_at).isoformat()}",
                f"owner_name: {_actor_display_name(getattr(instance, 'created_by', None))}",
            ],
        )
        if instance.deal_id:
            _append_deal_event(instance.deal_id, entry)
        if instance.lead_id:
            _append_lead_event(instance.lead_id, entry)
        for client_id in _task_related_client_ids(instance):
            _append_client_event(client_id, entry)

    if instance.status != TaskStatus.DONE:
        return

    previous = getattr(instance, "_previous_activity_state", None)
    if previous is not None and previous.type == ActivityType.TASK and previous.status == TaskStatus.DONE:
        return

    result_text = str(instance.result or "").strip()
    if not result_text:
        return

    happened_at = instance.completed_at or timezone.now()
    completion_event_type = _resolve_task_completion_event_type(instance) or "task"
    entry = _format_structured_event_entry(
        result_text=result_text,
        happened_at=happened_at,
        task_id=instance.pk,
        deal_id=instance.deal_id,
        event_type=completion_event_type,
        priority="low",
        extra_lines=[
            f"title: Задача: {instance.subject}",
            getattr(instance.task_type, "name", "") and f"task_type_name: {instance.task_type.name}",
            f"task_status_label: {_task_status_label(instance.status)}",
            instance.due_at and f"due_at: {timezone.localtime(instance.due_at).isoformat()}",
            f"owner_name: {_actor_display_name(getattr(instance, 'created_by', None))}",
            result_text and f"task_result: {result_text}",
        ],
    )
    _append_deal_event(instance.deal_id, entry)
    if instance.lead_id:
        _append_lead_event(instance.lead_id, entry)
    for client_id in _task_related_client_ids(instance):
        _append_client_event(client_id, entry)


@receiver(post_save, sender=Activity)
def activity_client_task_touch_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != ActivityType.TASK or instance.status != TaskStatus.DONE:
        return
    task_type = getattr(instance, "task_type", None)
    if task_type is None or not getattr(task_type, "auto_touch_on_done", False):
        return

    previous = getattr(instance, "_previous_activity_state", None)
    if previous is not None and previous.type == ActivityType.TASK and previous.status == TaskStatus.DONE:
        return

    touch_result_name = str(getattr(task_type, "touch_result", "") or "").strip()
    result_option = None
    if touch_result_name:
        touch_result_code = normalize_touch_channel_code(touch_result_name) or "touch_result"
        result_option, _ = TouchResult.objects.get_or_create(
            code=touch_result_code,
            defaults={"name": touch_result_name, "is_active": True},
        )

    Touch.objects.create(
        happened_at=instance.completed_at or timezone.now(),
        channel=instance.communication_channel,
        direction=TouchDirection.OUTGOING,
        result_option=result_option,
        summary="",
        next_step="",
        owner=instance.created_by,
        lead=instance.lead,
        deal=instance.deal,
        client=instance.client or getattr(instance.deal, "client", None) or getattr(instance.lead, "client", None),
        contact=instance.contact,
        task=instance,
    )


@receiver(post_save, sender=Activity)
def activity_task_auto_follow_up_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != ActivityType.TASK or instance.status != TaskStatus.DONE:
        return

    previous = getattr(instance, "_previous_activity_state", None)
    if previous is not None and previous.type == ActivityType.TASK and previous.status == TaskStatus.DONE:
        return

    task_type = getattr(instance, "task_type", None)
    auto_task_type = getattr(task_type, "auto_task_type", None)
    if task_type is None or not getattr(task_type, "auto_task_on_done", False) or auto_task_type is None:
        return

    communication_channel = instance.communication_channel if task_type_uses_communication_channel(auto_task_type) else None
    Activity.objects.create(
        type=ActivityType.TASK,
        subject=str(getattr(auto_task_type, "name", "") or "").strip() or instance.subject,
        description="",
        due_at=_resolve_auto_follow_up_due_at(instance),
        status=TaskStatus.TODO,
        priority=instance.priority or "medium",
        task_type=auto_task_type,
        communication_channel=communication_channel,
        deadline_reminder_offset_minutes=instance.deadline_reminder_offset_minutes,
        lead=instance.lead,
        deal=instance.deal,
        client=instance.client or getattr(instance.deal, "client", None) or getattr(instance.lead, "client", None),
        contact=instance.contact,
        created_by=instance.created_by,
    )


@receiver(post_save, sender=Activity)
def activity_task_company_note_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != ActivityType.TASK:
        return

    note_text = str(instance.company_note or "").strip()
    if not instance.save_company_note or not note_text:
        return

    previous = getattr(instance, "_previous_activity_state", None)
    previous_save_company_note = bool(getattr(previous, "save_company_note", False)) if previous else False
    previous_note_text = str(getattr(previous, "company_note", "") or "").strip() if previous else ""
    if not created and previous_save_company_note and previous_note_text == note_text:
        return

    note_entry = _format_company_note_entry(
        note_text=note_text,
        actor=instance.created_by,
        deal_id=instance.deal_id,
    )
    for client_id in _task_related_client_ids(instance):
        _append_client_note(client_id, note_entry)


@receiver(pre_save, sender=Deal)
def deal_previous_state_signal(sender, instance: Deal, **kwargs):
    instance._previous_deal_state = None
    if not instance.pk:
        return
    instance._previous_deal_state = (
        Deal.objects.filter(pk=instance.pk)
        .select_related("stage", "client", "owner", "source")
        .only(
            "is_won",
            "title",
            "stage_id",
            "stage__name",
            "client_id",
            "client__name",
            "owner_id",
            "owner__username",
            "owner__first_name",
            "owner__last_name",
            "source_id",
            "source__name",
            "amount",
            "close_date",
            "metadata",
        )
        .first()
    )


@receiver(pre_save, sender=Touch)
def touch_previous_state_signal(sender, instance: Touch, **kwargs):
    instance._previous_touch_state = None
    if not instance.pk:
        return
    instance._previous_touch_state = (
        Touch.objects.filter(pk=instance.pk)
        .select_related("channel", "result_option", "owner")
        .only(
            "deal_id",
            "lead_id",
            "client_id",
            "happened_at",
            "channel_id",
            "channel__name",
            "direction",
            "result_option_id",
            "result_option__name",
            "summary",
            "next_step",
            "next_step_at",
            "owner_id",
            "owner__username",
            "owner__first_name",
            "owner__last_name",
        )
        .first()
    )


@receiver(post_save, sender=Deal)
def deal_stage_change_events_signal(sender, instance: Deal, created, **kwargs):
    if created:
        return

    previous = getattr(instance, "_previous_deal_state", None)
    if previous is None:
        return

    previous_stage_id = getattr(previous, "stage_id", None)
    current_stage_id = getattr(instance, "stage_id", None)
    if previous_stage_id == current_stage_id:
        return

    previous_stage_name = getattr(previous.stage, "name", "") if getattr(previous, "stage", None) else ""
    current_stage_name = getattr(instance.stage, "name", "") if getattr(instance, "stage", None) else ""
    result_text = f"Статус сделки изменён: {previous_stage_name or 'Без этапа'} -> {current_stage_name or 'Без этапа'}"
    entry = _format_structured_event_entry(
        result_text=result_text,
        deal_id=instance.pk,
        event_type="system",
        priority="low",
        extra_lines=["title: Системное событие"],
    )
    _append_deal_event(instance.pk, entry)
    _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Deal)
def deal_system_events_signal(sender, instance: Deal, created, **kwargs):
    previous = getattr(instance, "_previous_deal_state", None)
    if created:
        entry = _format_structured_event_entry(
            result_text=f"Сделка создана: {instance.title}",
            deal_id=instance.pk,
            event_type="system",
            priority="low",
            extra_lines=["title: Системное событие"],
        )
        _append_deal_event(instance.pk, entry)
        _append_client_event(instance.client_id, entry)
        return

    if previous is None:
        return

    changes: list[str] = []
    if str(previous.title or "").strip() != str(instance.title or "").strip():
        changes.append(f"Название сделки изменено: {previous.title or 'Без названия'} -> {instance.title or 'Без названия'}")
    if getattr(previous, "owner_id", None) != getattr(instance, "owner_id", None):
        changes.append(
            f"Ответственный изменён: {_actor_display_name(getattr(previous, 'owner', None))} -> {_actor_display_name(getattr(instance, 'owner', None))}"
        )
    if getattr(previous, "amount", None) != getattr(instance, "amount", None):
        changes.append(f"Сумма изменена: {previous.amount or 0} -> {instance.amount or 0} {instance.currency}")
    if getattr(previous, "source_id", None) != getattr(instance, "source_id", None):
        previous_source = str(getattr(getattr(previous, "source", None), "name", "") or "Не выбран")
        current_source = str(getattr(getattr(instance, "source", None), "name", "") or "Не выбран")
        changes.append(f"Источник сделки изменён: {previous_source} -> {current_source}")
    if getattr(previous, "client_id", None) != getattr(instance, "client_id", None):
        previous_client = str(getattr(getattr(previous, "client", None), "name", "") or "Не выбрана")
        current_client = str(getattr(getattr(instance, "client", None), "name", "") or "Не выбрана")
        changes.append(f"Компания изменена: {previous_client} -> {current_client}")
    if getattr(previous, "close_date", None) != getattr(instance, "close_date", None):
        changes.append(
            f"План закрытия изменён: {previous.close_date.isoformat() if previous.close_date else 'Не указан'} -> {instance.close_date.isoformat() if instance.close_date else 'Не указан'}"
        )

    for change_text in changes:
        entry = _format_structured_event_entry(
            result_text=change_text,
            deal_id=instance.pk,
            event_type="system",
            priority="low",
            extra_lines=["title: Системное событие"],
        )
        _append_deal_event(instance.pk, entry)
        _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Deal)
def deal_failed_reason_events_signal(sender, instance: Deal, created, **kwargs):
    previous = getattr(instance, "_previous_deal_state", None)
    current_stage_code = str(getattr(getattr(instance, "stage", None), "code", "") or "").strip().lower()
    if current_stage_code != "failed":
        return

    current_reason = _extract_deal_failed_reason(instance)
    if not current_reason:
        return

    previous_stage_code = str(getattr(getattr(previous, "stage", None), "code", "") or "").strip().lower()
    previous_reason = _extract_deal_failed_reason(previous)

    if created or previous is None or previous_stage_code != "failed":
        result_text = f"Сделка провалена. Причина: {current_reason}"
    elif previous_reason != current_reason:
        result_text = f"Причина провала сделки обновлена: {current_reason}"
    else:
        return

    entry = _format_structured_event_entry(
        result_text=result_text,
        deal_id=instance.pk,
        event_type="system",
        priority="low",
        extra_lines=["title: Системное событие"],
    )
    _append_deal_event(instance.pk, entry)
    _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Deal)
def deal_completion_events_signal(sender, instance: Deal, created, **kwargs):
    if not instance.is_won:
        return

    previous = getattr(instance, "_previous_deal_state", None)
    if previous is not None and previous.is_won:
        return

    stage_name = getattr(instance.stage, "name", "") or "Успешно реализовано"
    result_text = f"Сделка завершена — {stage_name}"
    if instance.amount:
        result_text = f"{result_text} ({instance.amount} {instance.currency})"
    entry = _format_structured_event_entry(
        result_text=result_text,
        deal_id=instance.pk,
        event_type="system",
        priority="low",
        extra_lines=["title: Системное событие"],
    )
    _append_deal_event(instance.pk, entry)
    _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Touch)
def touch_deal_events_signal(sender, instance: Touch, created, **kwargs):
    if not instance.deal_id:
        return
    if not should_write_touch_timeline(instance):
        return

    previous = getattr(instance, "_previous_touch_state", None)
    result_label = _touch_result_label(instance)
    channel_label = _touch_channel_label(instance)
    direction_label = _touch_direction_label(instance.direction)
    base_text = result_label or str(instance.summary or "").strip() or f"{direction_label} касание"

    if created:
        entry = _format_structured_event_entry(
            result_text=f"Касание: {base_text}",
            happened_at=instance.happened_at,
            touch_id=instance.pk,
            deal_id=instance.deal_id,
            event_type="touch",
            priority="high",
            extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
        )
        _append_deal_event(instance.deal_id, entry)
        return

    if previous is None:
        return

    changed = (
        previous.channel_id != instance.channel_id
        or previous.direction != instance.direction
        or previous.result_option_id != instance.result_option_id
        or str(previous.summary or "") != str(instance.summary or "")
        or str(previous.next_step or "") != str(instance.next_step or "")
        or previous.next_step_at != instance.next_step_at
        or previous.owner_id != instance.owner_id
    )
    if not changed:
        return

    entry = _format_structured_event_entry(
        result_text=f"Касание обновлено: {base_text}",
        happened_at=instance.happened_at,
        touch_id=instance.pk,
        deal_id=instance.deal_id,
        event_type="touch",
        priority="high",
        extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
    )
    _replace_touch_event_in_deal(instance.deal_id, instance.pk, entry)


@receiver(post_save, sender=DealDocument)
def deal_document_events_signal(sender, instance: DealDocument, created, **kwargs):
    if not created:
        return

    document_name = str(instance.original_name or getattr(instance.file, "name", "") or "").strip() or f"Документ #{instance.pk}"
    entry = _format_structured_event_entry(
        result_text=f"Загружен документ: {document_name}",
        happened_at=instance.created_at,
        deal_id=instance.deal_id,
        event_type="document",
        priority="medium",
        extra_lines=[
            "title: Документ сделки",
            f"actor_name: {_actor_display_name(instance.uploaded_by)}",
            f"document_name: {document_name}",
            f"document_url: {_document_download_url(instance)}",
            "document_scope: deal",
        ],
    )
    _append_deal_event(instance.deal_id, entry)
    _append_client_event(instance.deal.client_id if instance.deal_id and instance.deal else None, entry)


@receiver(post_save, sender=ClientDocument)
def client_document_events_signal(sender, instance: ClientDocument, created, **kwargs):
    if not created:
        return

    document_name = str(instance.original_name or getattr(instance.file, "name", "") or "").strip() or f"Документ #{instance.pk}"
    entry = _format_structured_event_entry(
        result_text=f"Загружен документ: {document_name}",
        happened_at=instance.created_at,
        event_type="document",
        priority="medium",
        extra_lines=[
            "title: Документ компании",
            f"actor_name: {_actor_display_name(instance.uploaded_by)}",
            f"document_name: {document_name}",
            f"document_url: {_document_download_url(instance)}",
            "document_scope: company",
        ],
    )
    _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Touch)
def touch_lead_events_signal(sender, instance: Touch, created, **kwargs):
    if not instance.lead_id:
        return
    if not should_write_touch_timeline(instance):
        return

    previous = getattr(instance, "_previous_touch_state", None)
    result_label = _touch_result_label(instance)
    channel_label = _touch_channel_label(instance)
    direction_label = _touch_direction_label(instance.direction)
    base_text = result_label or str(instance.summary or "").strip() or f"{direction_label} касание"

    if created:
        entry = _format_structured_event_entry(
            result_text=f"Касание: {base_text}",
            happened_at=instance.happened_at,
            touch_id=instance.pk,
            event_type="touch",
            priority="high",
            extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
        )
        _append_lead_event(instance.lead_id, entry)
        return

    if previous is None:
        return

    if previous.lead_id != instance.lead_id:
        entry = _format_structured_event_entry(
            result_text=f"Касание: {base_text}",
            happened_at=instance.happened_at,
            touch_id=instance.pk,
            event_type="touch",
            priority="high",
            extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
        )
        _append_lead_event(instance.lead_id, entry)
        return

    changed = (
        previous.channel_id != instance.channel_id
        or previous.direction != instance.direction
        or previous.result_option_id != instance.result_option_id
        or str(previous.summary or "") != str(instance.summary or "")
        or str(previous.next_step or "") != str(instance.next_step or "")
        or previous.next_step_at != instance.next_step_at
        or previous.owner_id != instance.owner_id
    )
    if not changed:
        return

    entry = _format_structured_event_entry(
        result_text=f"Касание обновлено: {base_text}",
        happened_at=instance.happened_at,
        touch_id=instance.pk,
        event_type="touch",
        priority="high",
        extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
    )
    _replace_touch_event_in_lead(instance.lead_id, instance.pk, entry)


@receiver(post_save, sender=Touch)
def touch_client_events_signal(sender, instance: Touch, created, **kwargs):
    if not instance.client_id:
        return
    if not should_write_touch_timeline(instance):
        return

    previous = getattr(instance, "_previous_touch_state", None)
    result_label = _touch_result_label(instance)
    channel_label = _touch_channel_label(instance)
    direction_label = _touch_direction_label(instance.direction)
    base_text = result_label or str(instance.summary or "").strip() or f"{direction_label} касание"

    if created:
        entry = _format_structured_event_entry(
            result_text=f"Касание: {base_text}",
            happened_at=instance.happened_at,
            touch_id=instance.pk,
            deal_id=instance.deal_id,
            event_type="touch",
            priority="high",
            extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
        )
        _append_client_event(instance.client_id, entry)
        return

    if previous is None:
        return

    if previous.client_id != instance.client_id:
        entry = _format_structured_event_entry(
            result_text=f"Касание: {base_text}",
            happened_at=instance.happened_at,
            touch_id=instance.pk,
            deal_id=instance.deal_id,
            event_type="touch",
            priority="high",
            extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
        )
        _append_client_event(instance.client_id, entry)
        return

    changed = (
        previous.channel_id != instance.channel_id
        or previous.direction != instance.direction
        or previous.result_option_id != instance.result_option_id
        or str(previous.summary or "") != str(instance.summary or "")
        or str(previous.next_step or "") != str(instance.next_step or "")
        or previous.next_step_at != instance.next_step_at
        or previous.owner_id != instance.owner_id
    )
    if not changed:
        return

    entry = _format_structured_event_entry(
        result_text=f"Касание обновлено: {base_text}",
        happened_at=instance.happened_at,
        touch_id=instance.pk,
        deal_id=instance.deal_id,
        event_type="touch",
        priority="high",
        extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
    )
    _replace_touch_event_in_client(instance.client_id, instance.pk, entry)


@receiver(post_save, sender=Touch)
def touch_automation_drafts_signal(sender, instance: Touch, created, **kwargs):
    if bool(getattr(instance, "_skip_touch_automation", False)):
        return

    event_type, rule = resolve_touch_automation_rule(instance)

    allowed_draft_kinds: set[str] = set()
    allowed_queue_kinds: set[str] = set()
    allow_message_draft = False

    if event_type and rule is not None:
        if bool(getattr(rule, "create_message", False)):
            allow_message_draft = True

        if str(rule.create_touchpoint_mode or "").strip() == "draft":
            allowed_draft_kinds.add(AutomationDraftKind.TOUCH)

        should_create_next_step_draft = bool(
            getattr(rule, "next_step_template_id", None)
            and (
                bool(getattr(rule, "require_manager_confirmation", False))
                or not bool(getattr(rule, "allow_auto_create_task", False))
            )
        )
        if should_create_next_step_draft:
            allowed_draft_kinds.add(AutomationDraftKind.NEXT_STEP)

        ui_mode = str(getattr(rule, "ui_mode", "") or "").strip()
        should_create_attention_queue_item = bool(
            getattr(rule, "show_in_attention_queue", False)
            or getattr(rule, "require_manager_confirmation", False)
            or ui_mode == "needs_attention"
        )
        if should_create_attention_queue_item:
            allowed_queue_kinds.add(AutomationQueueItemKind.ATTENTION)

        should_create_next_step_queue_item = bool(
            getattr(rule, "next_step_template_id", None)
            and (
                getattr(rule, "require_manager_confirmation", False)
                or not getattr(rule, "allow_auto_create_task", False)
            )
        )
        if should_create_next_step_queue_item:
            allowed_queue_kinds.add(AutomationQueueItemKind.NEXT_STEP)

    _dismiss_pending_touch_automation_artifacts(
        instance,
        rule=rule if event_type else None,
        allowed_draft_kinds=allowed_draft_kinds,
        allowed_queue_kinds=allowed_queue_kinds,
        allow_message_draft=allow_message_draft,
    )

    if not event_type:
        return
    if rule is None:
        return

    if bool(getattr(rule, "create_message", False)):
        _upsert_touch_automation_message_draft(instance, rule)

    if str(rule.create_touchpoint_mode or "").strip() == "draft":
        _upsert_touch_automation_draft(instance, rule, AutomationDraftKind.TOUCH)
    elif created and str(rule.create_touchpoint_mode or "").strip() == "create":
        _create_touch_automation_touch(instance, rule)

    should_create_next_step_draft = AutomationDraftKind.NEXT_STEP in allowed_draft_kinds
    if should_create_next_step_draft:
        _upsert_touch_automation_draft(instance, rule, AutomationDraftKind.NEXT_STEP)

    should_create_attention_queue_item = AutomationQueueItemKind.ATTENTION in allowed_queue_kinds
    if should_create_attention_queue_item:
        _upsert_touch_automation_queue_item(instance, rule, AutomationQueueItemKind.ATTENTION)

    should_create_next_step_queue_item = AutomationQueueItemKind.NEXT_STEP in allowed_queue_kinds
    if should_create_next_step_queue_item:
        _upsert_touch_automation_queue_item(instance, rule, AutomationQueueItemKind.NEXT_STEP)

    if should_auto_create_touch_follow_up_task(instance, rule):
        upsert_touch_follow_up_task(instance, rule)


@receiver(m2m_changed, sender=Touch.deal_documents.through)
@receiver(m2m_changed, sender=Touch.client_documents.through)
def touch_documents_events_signal(sender, instance: Touch, action, reverse, **kwargs):
    if reverse or action not in {"post_add", "post_remove", "post_clear"}:
        return
    if not should_write_touch_timeline(instance):
        return

    result_label = _touch_result_label(instance)
    channel_label = _touch_channel_label(instance)
    direction_label = _touch_direction_label(instance.direction)
    base_text = result_label or str(instance.summary or "").strip() or f"{direction_label} касание"
    entry = _format_structured_event_entry(
        result_text=f"Касание обновлено: {base_text}",
        happened_at=instance.happened_at,
        touch_id=instance.pk,
        deal_id=instance.deal_id,
        event_type="touch",
        priority="high",
        extra_lines=_touch_event_extra_lines(instance, channel_label, result_label),
    )

    if instance.deal_id:
        _replace_touch_event_in_deal(instance.deal_id, instance.pk, entry)
    if instance.lead_id:
        _replace_touch_event_in_lead(instance.lead_id, instance.pk, entry)
    if instance.client_id:
        _replace_touch_event_in_client(instance.client_id, instance.pk, entry)
