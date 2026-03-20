from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import (
    AutomationMessageDraft,
    AutomationOutboundMessage,
    AutomationRule,
    Client,
    CommunicationChannel,
    Contact,
    Deal,
    DealStage,
    Touch,
)


class AutomationMessageDraftApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_automation_message",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="Acme")
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(title="Сделка для message drafts", stage=self.stage, client=self.company)
        self.channel = CommunicationChannel.objects.create(name="Telegram")
        self.rule = AutomationRule.objects.create(
            event_type="telegram_message_sent",
            ui_mode="history_only",
            ui_priority="medium",
            write_timeline=True,
            create_message=True,
            create_touchpoint_mode="none",
            is_active=True,
            sort_order=10,
        )

    def test_creating_touch_creates_pending_message_draft(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили сообщение клиенту",
            next_step_at=timezone.now() + timedelta(days=2),
            owner=self.user,
            deal=self.deal,
        )

        draft = AutomationMessageDraft.objects.filter(source_touch=touch, status="pending").first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.source_event_type, "telegram_message_sent")
        self.assertEqual(draft.deal_id, self.deal.pk)
        self.assertEqual(draft.client_id, self.company.pk)
        self.assertIn("Отправили сообщение", draft.message_text)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_confirm_message_draft_sends_email_and_logs_outbound(self):
        contact = Contact.objects.create(client=self.company, first_name="Иван", email="client@example.com")
        email_channel = CommunicationChannel.objects.create(name="Email")
        email_rule = AutomationRule.objects.create(
            event_type="email_sent",
            ui_mode="history_only",
            ui_priority="medium",
            write_timeline=True,
            create_message=True,
            create_touchpoint_mode="none",
            is_active=True,
            sort_order=20,
        )
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=email_channel,
            direction="outgoing",
            summary="Отправили письмо клиенту",
            owner=self.user,
            deal=self.deal,
            client=self.company,
            contact=contact,
        )
        draft = AutomationMessageDraft.objects.get(source_touch=touch, status="pending")

        response = self.client.post(
            reverse("automation-message-drafts-confirm", kwargs={"pk": draft.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "confirmed")
        self.assertEqual(response.data["last_outbound_status"], "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["client@example.com"])
        outbound = AutomationOutboundMessage.objects.get(message_draft=draft)
        self.assertEqual(outbound.status, "sent")
        self.assertEqual(outbound.channel_code, "email")
        self.assertEqual(outbound.recipient, "client@example.com")
        self.assertIsNotNone(outbound.sent_at)
        self.assertEqual(email_rule.event_type, "email_sent")

    def test_confirm_message_draft_marks_telegram_as_manual_required(self):
        contact = Contact.objects.create(client=self.company, first_name="Иван", telegram="@client_handle")
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили сообщение клиенту",
            owner=self.user,
            deal=self.deal,
            client=self.company,
            contact=contact,
        )
        draft = AutomationMessageDraft.objects.get(source_touch=touch, status="pending")

        response = self.client.post(
            reverse("automation-message-drafts-confirm", kwargs={"pk": draft.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        self.assertEqual(draft.status, "confirmed")
        self.assertEqual(response.data["last_outbound_status"], "manual_required")
        outbound = AutomationOutboundMessage.objects.get(message_draft=draft)
        self.assertEqual(outbound.status, "manual_required")
        self.assertEqual(outbound.channel_code, "telegram")
        self.assertEqual(outbound.recipient, "@client_handle")

    @patch("crm.services.automation_messages.send_telegram_chat_message")
    def test_confirm_message_draft_sends_telegram_when_contact_has_chat_id(self, send_telegram_mock):
        send_telegram_mock.return_value = {"ok": True, "payload": {"result": {"message_id": 101}}}
        contact = Contact.objects.create(client=self.company, first_name="Иван", telegram="555001")
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили сообщение в Telegram",
            owner=self.user,
            deal=self.deal,
            client=self.company,
            contact=contact,
        )
        draft = AutomationMessageDraft.objects.get(source_touch=touch, status="pending")

        response = self.client.post(
            reverse("automation-message-drafts-confirm", kwargs={"pk": draft.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_outbound_status"], "sent")
        send_telegram_mock.assert_called_once()
        outbound = AutomationOutboundMessage.objects.get(message_draft=draft)
        self.assertEqual(outbound.status, "sent")
        self.assertEqual(outbound.channel_code, "telegram")
        self.assertEqual(outbound.recipient, "555001")
        self.assertIsNotNone(outbound.sent_at)
