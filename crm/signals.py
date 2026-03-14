import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from audit.services import log_model_event
from crm.models import Activity, Deal, DealStage, Lead
from crm.services.lead_services import convert_lead_to_deal
from integrations.models import UserIntegrationProfile
from integrations.services.telegram import (
    build_task_notification_message,
    send_telegram_chat_message,
)


logger = logging.getLogger(__name__)


def _get_task_snapshot(instance: Activity) -> dict:
    return {
        "subject": instance.subject,
        "description": instance.description,
        "due_at": instance.due_at,
        "is_done": instance.is_done,
        "deal_id": instance.deal_id,
        "lead_id": instance.lead_id,
        "client_id": instance.client_id,
        "contact_id": instance.contact_id,
    }


def _task_changed(instance: Activity, previous_snapshot: dict | None) -> bool:
    if previous_snapshot is None:
        return True
    return previous_snapshot != _get_task_snapshot(instance)


def _get_task_recipients(instance: Activity):
    recipients = []
    candidates = [
        instance.created_by,
        instance.deal.owner if instance.deal_id and instance.deal else None,
        instance.lead.assigned_to if instance.lead_id and instance.lead else None,
    ]
    seen_ids = set()
    for user in candidates:
        if user is None or getattr(user, "pk", None) in seen_ids:
            continue
        seen_ids.add(user.pk)
        recipients.append(user)
    return recipients


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
def activity_task_previous_state_signal(sender, instance: Activity, **kwargs):
    if not instance.pk:
        instance._previous_task_snapshot = None
        return
    previous = Activity.objects.filter(pk=instance.pk).first()
    if previous is None or previous.type != "task":
        instance._previous_task_snapshot = None
        return
    instance._previous_task_snapshot = _get_task_snapshot(previous)


@receiver(post_save, sender=Activity)
def activity_task_telegram_notification_signal(sender, instance: Activity, created, **kwargs):
    if instance.type != "task":
        return

    previous_snapshot = getattr(instance, "_previous_task_snapshot", None)
    if not created and not _task_changed(instance, previous_snapshot):
        return

    message = build_task_notification_message(task=instance, created=created)
    for user in _get_task_recipients(instance):
        profile = UserIntegrationProfile.objects.filter(user=user).first()
        chat_id = str(getattr(profile, "telegram_chat_id", "") or "").strip()
        if not chat_id:
            continue
        try:
            send_telegram_chat_message(chat_id=chat_id, text=message)
        except Exception:
            logger.exception(
                "Failed to send task telegram notification. activity_id=%s user_id=%s",
                instance.pk,
                user.pk,
            )
