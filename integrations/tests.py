from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType
from integrations.models import UserIntegrationProfile


User = get_user_model()


class UserIntegrationProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="ivan", password="secret")

        profile = UserIntegrationProfile.objects.get(user=user)
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.telegram_chat_id, "")


class TaskDeadlineReminderCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="anna", password="secret")
        profile = self.user.integration_profile
        profile.telegram_chat_id = "123456789"
        profile.save(update_fields=["telegram_chat_id"])

    @patch("integrations.management.commands.send_task_deadline_reminders.send_telegram_chat_message")
    def test_sends_reminder_for_task_inside_30_minutes_window(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить КП",
            description="Нужно отправить коммерческое предложение",
            due_at=timezone.now() + timedelta(minutes=20),
            created_by=self.user,
        )

        out = StringIO()
        call_command("send_task_deadline_reminders", stdout=out)

        task.refresh_from_db()
        self.assertEqual(send_message_mock.call_count, 1)
        kwargs = send_message_mock.call_args.kwargs
        self.assertEqual(kwargs["chat_id"], "123456789")
        self.assertIn("Подготовить КП", kwargs["text"])
        self.assertIn("До дедлайна", kwargs["text"])
        self.assertIsNotNone(task.deadline_reminder_sent_at)
        self.assertIn("Sent deadline reminders: 1", out.getvalue())

    @patch("integrations.management.commands.send_task_deadline_reminders.send_telegram_chat_message")
    def test_does_not_send_reminder_for_task_outside_window(self, send_message_mock):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Позвонить клиенту",
            due_at=timezone.now() + timedelta(minutes=45),
            created_by=self.user,
        )

        call_command("send_task_deadline_reminders")

        task.refresh_from_db()
        send_message_mock.assert_not_called()
        self.assertIsNone(task.deadline_reminder_sent_at)

    @patch("integrations.management.commands.send_task_deadline_reminders.send_telegram_chat_message")
    def test_does_not_send_twice_for_same_task(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Проверить договор",
            due_at=timezone.now() + timedelta(minutes=10),
            created_by=self.user,
        )

        call_command("send_task_deadline_reminders")
        send_message_mock.reset_mock()

        call_command("send_task_deadline_reminders")

        task.refresh_from_db()
        send_message_mock.assert_not_called()
        self.assertIsNotNone(task.deadline_reminder_sent_at)
