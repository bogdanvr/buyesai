from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskReminderOffset


class TaskDeadlineReminderResetTests(TestCase):
    def test_resets_reminder_marker_when_due_date_changes(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Обновить счет",
            due_at=timezone.now() + timedelta(hours=2),
            deadline_reminder_sent_at=timezone.now(),
        )

        task.due_at = timezone.now() + timedelta(hours=4)
        task.save()
        task.refresh_from_db()

        self.assertIsNone(task.deadline_reminder_sent_at)

    def test_resets_reminder_marker_when_task_reopened(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подписать акт",
            due_at=timezone.now() + timedelta(hours=1),
        )
        Activity.objects.filter(pk=task.pk).update(
            is_done=True,
            deadline_reminder_sent_at=timezone.now(),
        )
        task.refresh_from_db()

        task.is_done = False
        task.save()
        task.refresh_from_db()

        self.assertIsNone(task.deadline_reminder_sent_at)

    def test_resets_reminder_marker_when_reminder_offset_changes(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Согласовать оплату",
            due_at=timezone.now() + timedelta(hours=2),
            deadline_reminder_offset_minutes=TaskReminderOffset.MINUTES_30,
            deadline_reminder_sent_at=timezone.now(),
        )

        task.deadline_reminder_offset_minutes = TaskReminderOffset.HOURS_1
        task.save()
        task.refresh_from_db()

        self.assertIsNone(task.deadline_reminder_sent_at)
