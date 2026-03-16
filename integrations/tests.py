from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from crm.models import Activity
from crm.models.activity import ActivityType, TaskReminderOffset
from integrations.models import UserIntegrationProfile


User = get_user_model()


class UserIntegrationProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="ivan", password="secret")

        profile = UserIntegrationProfile.objects.get(user=user)
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.email, "")
        self.assertEqual(profile.telegram_chat_id, "")


class TaskDeadlineReminderCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="anna", password="secret")
        profile = self.user.integration_profile
        profile.telegram_chat_id = "123456789"
        profile.email = "anna@example.com"
        profile.save(update_fields=["telegram_chat_id", "email"])

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
        self.assertEqual(kwargs["reply_markup"]["inline_keyboard"][0][0]["text"], "Принял")
        self.assertTrue(task.deadline_reminder_ack_token)
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
    def test_sends_reminder_using_custom_task_offset(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подтвердить встречу",
            due_at=timezone.now() + timedelta(hours=2, minutes=30),
            deadline_reminder_offset_minutes=TaskReminderOffset.HOURS_3,
            created_by=self.user,
        )

        call_command("send_task_deadline_reminders")

        task.refresh_from_db()
        self.assertEqual(send_message_mock.call_count, 1)
        self.assertIsNotNone(task.deadline_reminder_sent_at)

    @patch("integrations.management.commands.send_task_deadline_reminders.send_telegram_chat_message")
    def test_does_not_send_before_custom_task_offset_window(self, send_message_mock):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Проверить спецификацию",
            due_at=timezone.now() + timedelta(minutes=20),
            deadline_reminder_offset_minutes=TaskReminderOffset.MINUTES_10,
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

    @patch("integrations.management.commands.send_task_deadline_reminders.send_task_deadline_escalation_email")
    def test_sends_email_if_task_not_acknowledged_in_10_minutes(self, send_email_mock):
        send_email_mock.return_value = 1
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Согласовать смету",
            due_at=timezone.now() + timedelta(hours=1),
            created_by=self.user,
            deadline_reminder_sent_at=timezone.now() - timedelta(minutes=11),
            deadline_reminder_ack_token="abc123",
        )

        out = StringIO()
        call_command("send_task_deadline_reminders", stdout=out)

        task.refresh_from_db()
        self.assertEqual(send_email_mock.call_count, 1)
        kwargs = send_email_mock.call_args.kwargs
        self.assertEqual(kwargs["email"], "anna@example.com")
        self.assertEqual(kwargs["task"].pk, task.pk)
        self.assertIsNotNone(task.deadline_reminder_email_escalated_at)
        self.assertIn("escalated emails: 1", out.getvalue())

    @patch("integrations.management.commands.send_task_deadline_reminders.send_task_deadline_escalation_email")
    def test_does_not_send_email_if_task_already_acknowledged(self, send_email_mock):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Проверить приложение",
            due_at=timezone.now() + timedelta(hours=1),
            created_by=self.user,
            deadline_reminder_sent_at=timezone.now() - timedelta(minutes=11),
            deadline_reminder_ack_token="abc123",
            deadline_reminder_acknowledged_at=timezone.now() - timedelta(minutes=5),
        )

        call_command("send_task_deadline_reminders")

        task.refresh_from_db()
        send_email_mock.assert_not_called()
        self.assertIsNone(task.deadline_reminder_email_escalated_at)


class TelegramTaskAckWebhookTests(TestCase):
    @patch("integrations.services.telegram.answer_telegram_callback_query")
    @patch("integrations.services.telegram.edit_telegram_message_reply_markup")
    def test_acknowledges_task_from_telegram_callback(self, edit_markup_mock, answer_callback_mock):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Перезвонить клиенту",
            deadline_reminder_ack_token="token123",
        )

        response = self.client.post(
            "/api/v1/webhooks/telegram/",
            data={
                "update_id": 1001,
                "callback_query": {
                    "id": "callback-1",
                    "data": f"task_ack:{task.pk}:token123",
                    "message": {
                        "message_id": 77,
                        "chat": {"id": "123456789"},
                    },
                },
            },
            content_type="application/json",
        )

        task.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(task.deadline_reminder_acknowledged_at)
        answer_callback_mock.assert_called_once()
        edit_markup_mock.assert_called_once()
