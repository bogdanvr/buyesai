from django.db import transaction
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskStatus


@transaction.atomic
def create_activity(
    *,
    type: str,
    subject: str,
    description: str = "",
    lead=None,
    deal=None,
    client=None,
    contact=None,
    due_at=None,
    created_by=None,
) -> Activity:
    return Activity.objects.create(
        type=type,
        subject=subject,
        description=description,
        lead=lead,
        deal=deal,
        client=client,
        contact=contact,
        due_at=due_at,
        created_by=created_by,
    )


@transaction.atomic
def complete_activity(*, activity: Activity) -> Activity:
    if activity.type == ActivityType.TASK:
        activity.status = TaskStatus.DONE
    activity.is_done = True
    activity.completed_at = activity.completed_at or timezone.now()
    activity.save(update_fields=["status", "is_done", "completed_at", "updated_at"])
    return activity
