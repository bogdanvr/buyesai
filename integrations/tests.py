from datetime import timedelta
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from crm.models import Activity, Lead
from crm.models.activity import ActivityType, TaskReminderOffset, TaskStatus
from integrations.models import LlmProviderAccount, UserIntegrationProfile
from integrations.services.llm_router import resolve_touch_analysis_llm_target


User = get_user_model()


class UserIntegrationProfileTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username="ivan", password="secret")

        profile = UserIntegrationProfile.objects.get(user=user)
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.email, "")
        self.assertEqual(profile.telegram_chat_id, "")


@override_settings(INTEGRATIONS_SECRET_KEY="integration-secret-for-tests")
class LlmProviderAccountTests(TestCase):
    def test_encrypts_and_decrypts_api_key(self):
        provider = LlmProviderAccount.objects.create(
            name="DeepSeek Prod",
            provider="deepseek",
            api_style="openai_compatible",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )

        provider.set_api_key("super-secret-token")
        provider.save(update_fields=["api_key_encrypted", "api_key_last4", "updated_at"])
        provider.refresh_from_db()

        self.assertNotEqual(provider.api_key_encrypted, "super-secret-token")
        self.assertEqual(provider.api_key_last4, "oken")
        self.assertEqual(provider.api_key_masked, "****oken")
        self.assertEqual(provider.get_api_key(), "super-secret-token")

    def test_router_prefers_provider_account_for_touch_analysis(self):
        fallback_provider = LlmProviderAccount.objects.create(
            name="Fallback",
            provider="openai",
            api_style="openai_compatible",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            use_for_touch_analysis=True,
            priority=50,
        )
        fallback_provider.set_api_key("fallback-secret")
        fallback_provider.save(update_fields=["api_key_encrypted", "api_key_last4", "updated_at"])

        primary_provider = LlmProviderAccount.objects.create(
            name="Primary",
            provider="yandexgpt",
            api_style="openai_compatible",
            base_url="https://llm.api.cloud.yandex.net/v1",
            model="yandexgpt",
            use_for_touch_analysis=True,
            priority=10,
        )
        primary_provider.set_api_key("primary-secret")
        primary_provider.save(update_fields=["api_key_encrypted", "api_key_last4", "updated_at"])

        target = resolve_touch_analysis_llm_target()

        self.assertIsNotNone(target)
        self.assertEqual(target.provider_account_id, primary_provider.id)
        self.assertEqual(target.api_key, "primary-secret")


@override_settings(INTEGRATIONS_SECRET_KEY="integration-secret-for-tests")
class LlmProviderAccountApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="llm_admin", password="secret", is_staff=True)
        self.client.force_login(self.user)

    def test_create_provider_masks_api_key_in_response(self):
        response = self.client.post(
            reverse("integrations-llm-provider-list"),
            data=json.dumps({
                "name": "Yandex Studio",
                "provider": "yandexgpt",
                "api_style": "openai_compatible",
                "base_url": "https://llm.api.cloud.yandex.net/v1",
                "model": "yandexgpt",
                "api_key": "yandex-secret-key",
                "use_for_touch_analysis": True,
                "priority": 15,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertNotIn("api_key", payload)
        self.assertTrue(payload["has_api_key"])
        self.assertEqual(payload["api_key_masked"], "****-key")

        provider = LlmProviderAccount.objects.get(name="Yandex Studio")
        self.assertEqual(provider.get_api_key(), "yandex-secret-key")


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

    @patch("integrations.management.commands.send_task_deadline_reminders.send_telegram_chat_message")
    def test_does_not_send_reminder_for_canceled_task(self, send_message_mock):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отмененная задача",
            due_at=timezone.now() + timedelta(minutes=10),
            created_by=self.user,
            status=TaskStatus.CANCELED,
        )

        call_command("send_task_deadline_reminders")

        task.refresh_from_db()
        send_message_mock.assert_not_called()
        self.assertIsNone(task.deadline_reminder_sent_at)

    @override_settings(TASK_REMINDER_ESCALATION_MINUTES=10)
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


class LeadAssignmentNotificationCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="anna_lead", password="secret", is_staff=True)
        profile = self.user.integration_profile
        profile.telegram_chat_id = "555001"
        profile.email = "anna_lead@example.com"
        profile.save(update_fields=["telegram_chat_id", "email"])

    @patch("integrations.management.commands.send_lead_assignment_notifications.send_telegram_chat_message")
    def test_sends_lead_notification_to_telegram_with_accept_button(self, send_message_mock):
        send_message_mock.return_value = {"ok": True}
        lead = Lead.objects.create(title="Новый лид", company="Acme")

        out = StringIO()
        call_command("send_lead_assignment_notifications", stdout=out)

        lead.refresh_from_db()
        self.assertEqual(send_message_mock.call_count, 1)
        kwargs = send_message_mock.call_args.kwargs
        self.assertEqual(kwargs["chat_id"], "555001")
        self.assertIn("Новый лид", kwargs["text"])
        self.assertEqual(kwargs["reply_markup"]["inline_keyboard"][0][0]["text"], "Принять")
        self.assertTrue(lead.assignment_notification_token)
        self.assertIsNotNone(lead.assignment_notification_sent_at)
        self.assertIn("Sent lead notifications: 1", out.getvalue())

    def test_sends_email_if_lead_not_accepted_in_time(self):
        lead = Lead.objects.create(
            title="Лид без ответственного",
            company="Beta",
            assignment_notification_sent_at=timezone.now() - timedelta(minutes=11),
            assignment_notification_token="leadtoken123",
        )

        call_command("send_lead_assignment_notifications")

        lead.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Принять", mail.outbox[0].alternatives[0][0])
        self.assertIsNotNone(lead.assignment_notification_email_escalated_at)


class LeadAcceptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lead_owner", password="secret", is_staff=True)
        profile = self.user.integration_profile
        profile.telegram_chat_id = "888999"
        profile.email = "lead_owner@example.com"
        profile.save(update_fields=["telegram_chat_id", "email"])

    @patch("integrations.services.telegram.answer_telegram_callback_query")
    @patch("integrations.services.telegram.edit_telegram_message_reply_markup")
    def test_accepts_lead_from_telegram_callback(self, edit_markup_mock, answer_callback_mock):
        lead = Lead.objects.create(
            title="Лид из Telegram",
            assignment_notification_token="lead123",
        )

        response = self.client.post(
            "/api/v1/webhooks/telegram/",
            data={
                "update_id": 2001,
                "callback_query": {
                    "id": "lead-callback-1",
                    "data": f"lead_accept:{lead.pk}:lead123",
                    "from": {"id": "888999"},
                    "message": {
                        "message_id": 88,
                        "chat": {"id": "888999"},
                    },
                },
            },
            content_type="application/json",
        )

        lead.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(lead.assigned_to, self.user)
        self.assertIsNotNone(lead.assignment_notification_accepted_at)
        answer_callback_mock.assert_called_once()
        edit_markup_mock.assert_called_once()

    def test_accepts_lead_from_email_link(self):
        lead = Lead.objects.create(
            title="Лид из Email",
            assignment_notification_token="email123",
        )

        from integrations.services.email import build_lead_accept_email_token

        token = build_lead_accept_email_token(lead=lead, user=self.user)
        response = self.client.get(f"/api/v1/leads/accept/?token={token}")

        lead.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(lead.assigned_to, self.user)
