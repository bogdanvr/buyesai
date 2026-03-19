import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from audit.services import log_model_event
from crm.models import Activity, Client, Deal, DealStage, Lead, Touch
from crm.models.activity import ActivityType, TaskStatus, TaskTypeGroup
from crm.models.touch import TouchDirection
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
    deal_id: int | None = None,
) -> str:
    timestamp = timezone.localtime(happened_at or timezone.now()).strftime("%d.%m.%Y %H:%M")
    lines = [timestamp, f"Результат: {str(result_text or '').strip()}"]
    if task_id:
        lines.append(f"task_id: {task_id}")
    if deal_id:
        lines.append(f"deal_id: {deal_id}")
    return "\n".join(lines)


def _prepend_event(existing: str, entry: str) -> str:
    current = str(existing or "").strip()
    return entry if not current else f"{entry}\n\n{current}"


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


def _task_type_group(instance: Activity) -> str:
    task_type = getattr(instance, "task_type", None)
    return str(getattr(task_type, "group", "") or "").strip()


@receiver(post_save, sender=Lead)
def lead_audit_signal(sender, instance: Lead, created, **kwargs):
    log_model_event(instance=instance, action="lead.created" if created else "lead.updated")


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
    if instance.type != ActivityType.TASK or instance.status != TaskStatus.DONE:
        return

    previous = getattr(instance, "_previous_activity_state", None)
    if previous is not None and previous.type == ActivityType.TASK and previous.status == TaskStatus.DONE:
        return

    result_text = str(instance.result or "").strip()
    if not result_text:
        return

    happened_at = instance.completed_at or timezone.now()
    entry = _format_structured_event_entry(
        result_text=result_text,
        happened_at=happened_at,
        task_id=instance.pk,
        deal_id=instance.deal_id,
    )
    _append_deal_event(instance.deal_id, entry)
    for client_id in _task_related_client_ids(instance):
        _append_client_event(client_id, entry)


@receiver(post_save, sender=Activity)
def activity_client_task_touch_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != ActivityType.TASK or instance.status != TaskStatus.DONE:
        return
    if _task_type_group(instance) != TaskTypeGroup.CLIENT_TASK:
        return

    previous = getattr(instance, "_previous_activity_state", None)
    if previous is not None and previous.type == ActivityType.TASK and previous.status == TaskStatus.DONE:
        return

    summary = str(instance.result or "").strip() or str(instance.subject or "").strip() or f"Завершена задача #{instance.pk}"
    Touch.objects.create(
        happened_at=instance.completed_at or timezone.now(),
        channel=instance.communication_channel,
        direction=TouchDirection.OUTGOING,
        summary=summary,
        owner=instance.created_by,
        lead=instance.lead,
        deal=instance.deal,
        client=instance.client or getattr(instance.deal, "client", None) or getattr(instance.lead, "client", None),
        contact=instance.contact,
        task=instance,
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
        .select_related("stage", "client")
        .only("is_won", "title", "stage_id", "stage__name", "client_id", "metadata")
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
    )
    _append_deal_event(instance.pk, entry)


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
    )
    _append_deal_event(instance.pk, entry)
    _append_client_event(instance.client_id, entry)
