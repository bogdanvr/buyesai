import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from audit.services import log_model_event
from crm.models import Activity, Client, Deal, DealStage, Lead, Touch, TouchResult
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


def _touch_result_label(instance: Touch) -> str:
    return str(getattr(getattr(instance, "result_option", None), "name", "") or "").strip()


def _touch_channel_label(instance: Touch) -> str:
    return str(getattr(getattr(instance, "channel", None), "name", "") or "").strip()


def _touch_direction_label(direction: str) -> str:
    return TouchDirection.OUTGOING.label if direction == TouchDirection.OUTGOING else TouchDirection.INCOMING.label


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


def _resolve_auto_follow_up_due_at(instance: Activity):
    now = instance.completed_at or timezone.now()
    due_at = getattr(instance, "due_at", None)
    if due_at is None:
        return now
    return due_at if due_at >= now else now


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
    if instance.type != ActivityType.TASK:
        return

    if created and instance.deal_id:
        entry = _format_structured_event_entry(
            result_text=f"Создана задача: {instance.subject}",
            happened_at=instance.created_at,
            task_id=instance.pk,
            deal_id=instance.deal_id,
            event_type="task",
            priority="medium" if instance.status in ACTIVE_TASK_STATUSES else "low",
        )
        _append_deal_event(instance.deal_id, entry)

    if instance.status != TaskStatus.DONE:
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
        event_type="task",
        priority="low",
    )
    _append_deal_event(instance.deal_id, entry)
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
        result_option, _ = TouchResult.objects.get_or_create(
            name=touch_result_name,
            defaults={"is_active": True},
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

    communication_channel = instance.communication_channel if getattr(auto_task_type, "group", "") == TaskTypeGroup.CLIENT_TASK else None
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
    )
    _append_deal_event(instance.pk, entry)


@receiver(post_save, sender=Deal)
def deal_system_events_signal(sender, instance: Deal, created, **kwargs):
    previous = getattr(instance, "_previous_deal_state", None)
    if created:
        entry = _format_structured_event_entry(
            result_text=f"Сделка создана: {instance.title}",
            deal_id=instance.pk,
            event_type="system",
            priority="low",
        )
        _append_deal_event(instance.pk, entry)
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
        event_type="system",
        priority="low",
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
    )
    _append_deal_event(instance.pk, entry)
    _append_client_event(instance.client_id, entry)


@receiver(post_save, sender=Touch)
def touch_deal_events_signal(sender, instance: Touch, created, **kwargs):
    if not instance.deal_id:
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
            extra_lines=[
                channel_label and f"Канал: {channel_label}",
                instance.summary and f"Содержание: {instance.summary}",
                instance.next_step and f"Следующий шаг: {instance.next_step}",
            ],
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
        extra_lines=[
            channel_label and f"Канал: {channel_label}",
            instance.summary and f"Содержание: {instance.summary}",
            instance.next_step and f"Следующий шаг: {instance.next_step}",
        ],
    )
    _append_deal_event(instance.deal_id, entry)
