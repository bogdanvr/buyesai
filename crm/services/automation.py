from django.utils import timezone

from crm.models import Activity, AutomationRule, Touch
from crm.models.activity import ActivityType, TaskPriority, TaskStatus, TaskTypeGroup
from crm.models.touch import resolve_touch_event_type


def resolve_touch_automation_rule(instance: Touch) -> tuple[str, AutomationRule | None]:
    event_type = resolve_touch_event_type(
        channel_code=getattr(getattr(instance, "channel", None), "name", ""),
        direction=str(instance.direction or "").strip().lower(),
        result_code=str(getattr(getattr(instance, "result_option", None), "code", "") or "").strip().lower(),
    )
    if not event_type:
        return "", None
    rule = (
        AutomationRule.objects.filter(event_type=event_type, is_active=True)
        .select_related("default_outcome", "next_step_template")
        .first()
    )
    return event_type, rule


def should_write_touch_timeline(instance: Touch) -> bool:
    _, rule = resolve_touch_automation_rule(instance)
    if rule is None:
        return True
    return bool(getattr(rule, "write_timeline", True))


def should_auto_create_touch_follow_up_task(instance: Touch, rule: AutomationRule | None) -> bool:
    if rule is None:
        return False
    if not getattr(rule, "next_step_template_id", None):
        return False
    if not getattr(rule, "allow_auto_create_task", False):
        return False
    if getattr(rule, "require_manager_confirmation", False):
        return False
    return True


def upsert_touch_follow_up_task(instance: Touch, rule: AutomationRule | None) -> Activity | None:
    if not should_auto_create_touch_follow_up_task(instance, rule):
        return None
    subject = str(getattr(getattr(rule, "next_step_template", None), "name", "") or instance.next_step or "").strip()
    if not subject:
        return None
    due_at = getattr(instance, "next_step_at", None) or timezone.now()
    client = instance.client or getattr(instance.deal, "client", None) or getattr(instance.lead, "client", None)
    communication_channel = getattr(instance, "channel", None)
    task_type_group = TaskTypeGroup.CLIENT_TASK if communication_channel is not None else ""

    existing = (
        Activity.objects.filter(
            type=ActivityType.TASK,
            subject=subject,
            deal=instance.deal,
            lead=instance.lead,
            client=client,
            contact=instance.contact,
        )
        .order_by("-id")
        .first()
    )

    if existing is not None:
        update_fields = []
        if existing.status not in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}:
            existing.status = TaskStatus.TODO
            update_fields.extend(["status", "is_done", "completed_at"])
        if existing.due_at != due_at:
            existing.due_at = due_at
            update_fields.append("due_at")
        if existing.communication_channel_id != getattr(communication_channel, "id", None):
            existing.communication_channel = communication_channel if task_type_group == TaskTypeGroup.CLIENT_TASK else None
            update_fields.append("communication_channel")
        if existing.client_id != getattr(client, "id", None):
            existing.client = client
            update_fields.append("client")
        if existing.deal_id != getattr(instance, "deal_id", None):
            existing.deal = instance.deal
            update_fields.append("deal")
        if existing.lead_id != getattr(instance, "lead_id", None):
            existing.lead = instance.lead
            update_fields.append("lead")
        if existing.contact_id != getattr(instance, "contact_id", None):
            existing.contact = instance.contact
            update_fields.append("contact")
        if update_fields:
            existing.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
        return existing

    return Activity.objects.create(
        type=ActivityType.TASK,
        subject=subject,
        description=str(instance.summary or "").strip(),
        due_at=due_at,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        communication_channel=communication_channel if task_type_group == TaskTypeGroup.CLIENT_TASK else None,
        lead=instance.lead,
        deal=instance.deal,
        client=client,
        contact=instance.contact,
        created_by=instance.owner,
    )
