import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from audit.services import log_model_event
from crm.models import Activity, Deal, DealStage, Lead
from crm.models.activity import ActivityType
from crm.services.lead_services import convert_lead_to_deal


logger = logging.getLogger(__name__)


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

    if instance.is_done:
        instance.deadline_reminder_sent_at = None
        return

    if not instance.pk:
        return

    previous = (
        Activity.objects.filter(pk=instance.pk)
        .only("type", "due_at", "is_done", "deadline_reminder_sent_at")
        .first()
    )
    if previous is None or previous.type != ActivityType.TASK:
        return

    due_at_changed = previous.due_at != instance.due_at
    reopened = previous.is_done and not instance.is_done
    if due_at_changed or reopened:
        instance.deadline_reminder_sent_at = None
        if instance.due_at and instance.due_at <= timezone.now():
            instance.deadline_reminder_sent_at = None
