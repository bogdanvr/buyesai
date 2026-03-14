from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

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


class TaskTelegramNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="anna", password="secret")
        profile = self.user.integration_profile
        profile.telegram_chat_id = "123456789"
        profile.save(update_fields=["telegram_chat_id"])

    @patch("crm.signals.send_telegram_chat_message")
    def test_task_creation_sends_telegram_notification(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}

        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить КП",
            description="Нужно отправить коммерческое предложение",
            created_by=self.user,
        )

        send_message_mock.assert_called_once()
        kwargs = send_message_mock.call_args.kwargs
        self.assertEqual(kwargs["chat_id"], "123456789")
        self.assertIn("Подготовить КП", kwargs["text"])
        self.assertEqual(task.created_by, self.user)

    @patch("crm.signals.send_telegram_chat_message")
    def test_non_task_activity_does_not_send_telegram_notification(self, send_message_mock):
        Activity.objects.create(
            type=ActivityType.NOTE,
            subject="Обычная заметка",
            created_by=self.user,
        )

        send_message_mock.assert_not_called()

    @patch("crm.signals.send_telegram_chat_message")
    def test_task_update_sends_notification_only_on_meaningful_change(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Позвонить клиенту",
            created_by=self.user,
        )
        send_message_mock.reset_mock()

        task.save()
        send_message_mock.assert_not_called()

        task.is_done = True
        task.save()
        send_message_mock.assert_called_once()
        self.assertIn("Задача обновлена", send_message_mock.call_args.kwargs["text"])
