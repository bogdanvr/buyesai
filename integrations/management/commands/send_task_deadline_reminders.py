import logging
import math
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskReminderOffset
from integrations.models import UserIntegrationProfile
from integrations.services.telegram import (
    build_task_deadline_reminder_message,
    send_telegram_chat_message,
)


logger = logging.getLogger(__name__)


def get_task_recipients(task: Activity):
    recipients = []
    candidates = [
        task.created_by,
        task.deal.owner if task.deal_id and task.deal else None,
        task.lead.assigned_to if task.lead_id and task.lead else None,
    ]
    seen_ids = set()
    for user in candidates:
        user_id = getattr(user, "pk", None)
        if user is None or user_id in seen_ids:
            continue
        seen_ids.add(user_id)
        recipients.append(user)
    return recipients


class Command(BaseCommand):
    help = "Отправляет Telegram-напоминания по задачам за выбранное время до дедлайна."

    def handle(self, *args, **options):
        now = timezone.now()
        reminder_threshold = now + timedelta(minutes=TaskReminderOffset.HOURS_3)
        tasks = (
            Activity.objects.select_related("created_by", "deal__owner", "lead__assigned_to", "deal", "client")
            .filter(
                type=ActivityType.TASK,
                is_done=False,
                due_at__isnull=False,
                due_at__gt=now,
                due_at__lte=reminder_threshold,
                deadline_reminder_sent_at__isnull=True,
            )
            .order_by("due_at", "id")
        )

        sent_count = 0
        for task in tasks:
            reminder_offset = int(
                getattr(task, "deadline_reminder_offset_minutes", TaskReminderOffset.MINUTES_30)
                or TaskReminderOffset.MINUTES_30
            )
            reminder_at = task.due_at - timedelta(minutes=reminder_offset)
            if reminder_at > now or task.due_at <= now:
                continue
            minutes_left = max(1, math.ceil((task.due_at - now).total_seconds() / 60))
            message = build_task_deadline_reminder_message(task=task, minutes_left=minutes_left)
            reminder_sent = False

            for user in get_task_recipients(task):
                profile = UserIntegrationProfile.objects.filter(user=user).only("telegram_chat_id").first()
                chat_id = str(getattr(profile, "telegram_chat_id", "") or "").strip()
                if not chat_id:
                    continue
                try:
                    result = send_telegram_chat_message(chat_id=chat_id, text=message)
                except Exception:
                    logger.exception(
                        "Failed to send deadline reminder. activity_id=%s user_id=%s",
                        task.pk,
                        user.pk,
                    )
                    continue
                if result.get("ok"):
                    reminder_sent = True

            if reminder_sent:
                Activity.objects.filter(pk=task.pk).update(deadline_reminder_sent_at=now)
                sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent deadline reminders: {sent_count}"))
