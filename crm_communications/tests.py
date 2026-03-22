from datetime import timedelta
from email.message import EmailMessage
from io import StringIO
import tempfile

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from crm.models import Client, Contact, Deal, DealStage, Touch
from crm_communications.email_outbound import EmailOutboundMessageService
from crm_communications.models import (
    AttemptStatus,
    CommunicationChannelCode,
    Conversation,
    ConversationRoute,
    DeliveryFailureQueue,
    ErrorClass,
    Message,
    MessageAttachment,
    MessageDirection,
    MessageStatus,
    MessageWebhookEvent,
    MessageType,
    WebhookProcessingStatus,
)
from crm_communications.email_inbound import EmailInboundService
from crm_communications.services import (
    COMMUNICATION_CHANNEL_LABELS,
    ConversationBindingService,
    ConversationResolverService,
    MAX_SEND_ATTEMPTS,
    MessageQueueService,
    TelegramOutboundMessageService,
)


class ConversationResolverServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_staff",
            password="testpass123",
            is_staff=True,
        )
        self.client_company = Client.objects.create(name="Acme")
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_comm",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.stage_final = DealStage.objects.create(
            name="Закрыто",
            code="closed_comm",
            order=100,
            is_active=True,
            is_final=True,
        )

    def test_resolves_contact_and_single_active_deal_by_email(self):
        contact = Contact.objects.create(
            client=self.client_company,
            first_name="Ivan",
            email="ivan@example.com",
        )
        deal = Deal.objects.create(
            title="Активная сделка",
            client=self.client_company,
            stage=self.stage_active,
        )

        resolution = ConversationResolverService.resolve_for_email(email="ivan@example.com")

        self.assertEqual(resolution.client, self.client_company)
        self.assertEqual(resolution.contact, contact)
        self.assertEqual(resolution.deal, deal)
        self.assertFalse(resolution.requires_manual_binding)
        self.assertIn("matched_by_contact_email", resolution.resolution_notes)
        self.assertIn("matched_by_single_active_deal", resolution.resolution_notes)

    def test_marks_manual_binding_when_client_has_multiple_active_deals(self):
        Contact.objects.create(
            client=self.client_company,
            first_name="Ivan",
            email="ivan@example.com",
        )
        Deal.objects.create(
            title="Сделка 1",
            client=self.client_company,
            stage=self.stage_active,
        )
        Deal.objects.create(
            title="Сделка 2",
            client=self.client_company,
            stage=self.stage_active,
        )

        resolution = ConversationResolverService.resolve_for_email(email="ivan@example.com")

        self.assertEqual(resolution.client, self.client_company)
        self.assertIsNone(resolution.deal)
        self.assertTrue(resolution.requires_manual_binding)
        self.assertIn("requires_manual_binding", resolution.resolution_notes)

    def test_route_has_priority_over_active_deal_selection(self):
        contact = Contact.objects.create(
            client=self.client_company,
            first_name="Ivan",
            email="ivan@example.com",
        )
        old_deal = Deal.objects.create(
            title="Ранее привязанная сделка",
            client=self.client_company,
            stage=self.stage_active,
        )
        Deal.objects.create(
            title="Новая активная сделка",
            client=self.client_company,
            stage=self.stage_active,
        )
        conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.EMAIL,
            client=self.client_company,
            contact=contact,
        )
        ConversationBindingService.bind_conversation(
            conversation=conversation,
            channel=CommunicationChannelCode.EMAIL,
            route_type="email_thread",
            route_key="thread-1",
            client=self.client_company,
            contact=contact,
            deal=old_deal,
            resolved_by=self.user,
            resolution_source="manual",
        )

        resolution = ConversationResolverService.resolve_for_email(
            email="ivan@example.com",
            route_type="email_thread",
            route_key="thread-1",
        )

        self.assertEqual(resolution.deal, old_deal)
        self.assertIsNotNone(resolution.matched_route)
        self.assertIn("matched_by_route", resolution.resolution_notes)

    def test_resolves_telegram_via_participant_binding(self):
        contact = Contact.objects.create(
            client=self.client_company,
            first_name="Ivan",
            telegram="123456789",
        )
        deal = Deal.objects.create(
            title="Сделка Telegram",
            client=self.client_company,
            stage=self.stage_active,
        )
        ConversationBindingService.ensure_participant_binding(
            channel=CommunicationChannelCode.TELEGRAM,
            external_participant_key="telegram:123456789",
            client=self.client_company,
            contact=contact,
            external_display_name="Ivan TG",
        )

        resolution = ConversationResolverService.resolve_for_telegram(
            external_participant_key="123456789",
        )

        self.assertEqual(resolution.client, self.client_company)
        self.assertEqual(resolution.contact, contact)
        self.assertEqual(resolution.deal, deal)
        self.assertIn("matched_by_participant_binding", resolution.resolution_notes)


class ConversationBindingServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_bind_staff",
            password="testpass123",
            is_staff=True,
        )
        self.client_company = Client.objects.create(name="Beta")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Olga",
            email="olga@example.com",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_bind",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Сделка Beta",
            client=self.client_company,
            stage=self.stage_active,
        )
        self.conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.EMAIL,
            requires_manual_binding=True,
        )

    def test_bind_conversation_updates_primary_route_and_aggregate_fields(self):
        route = ConversationBindingService.bind_conversation(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            route_type="email_thread",
            route_key="thread-beta",
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            resolved_by=self.user,
            resolution_source="manual",
        )

        self.conversation.refresh_from_db()
        self.assertTrue(route.is_primary)
        self.assertIsNotNone(route.resolved_at)
        self.assertEqual(self.conversation.client, self.client_company)
        self.assertEqual(self.conversation.contact, self.contact)
        self.assertEqual(self.conversation.deal, self.deal)
        self.assertFalse(self.conversation.requires_manual_binding)


class MessageQueueServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_queue_staff",
            password="testpass123",
            is_staff=True,
        )
        self.client_company = Client.objects.create(name="Queue Co")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Pavel",
            email="pavel@example.com",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_queue",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Queue Deal",
            client=self.client_company,
            stage=self.stage_active,
        )
        self.conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.EMAIL,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
        )

    def create_outgoing_message(self) -> Message:
        return Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Тестовая отправка",
            body_text="Сообщение клиенту",
            body_preview="Сообщение клиенту",
        )

    def test_enqueue_message_moves_message_to_queued(self):
        message = self.create_outgoing_message()

        MessageQueueService.enqueue_message(message=message)
        message.refresh_from_db()

        self.assertEqual(message.status, MessageStatus.QUEUED)
        self.assertIsNotNone(message.queued_at)
        self.assertIsNotNone(message.next_attempt_at)
        self.assertFalse(message.requires_manual_retry)

    def test_begin_send_attempt_creates_started_attempt(self):
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)

        attempt = MessageQueueService.begin_send_attempt(message=message)
        message.refresh_from_db()

        self.assertEqual(message.status, MessageStatus.SENDING)
        self.assertIsNotNone(message.sending_started_at)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.status, AttemptStatus.STARTED)

    def test_temporary_failure_schedules_retry(self):
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)
        attempt = MessageQueueService.begin_send_attempt(message=message)
        before = timezone.now()

        MessageQueueService.mark_attempt_failed(
            message=message,
            attempt=attempt,
            error_class=ErrorClass.TEMPORARY,
            error_code="smtp_timeout",
            error_message="Временная ошибка SMTP",
        )
        message.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(message.status, MessageStatus.QUEUED)
        self.assertIsNotNone(message.next_attempt_at)
        self.assertGreaterEqual(message.next_attempt_at, before + timedelta(minutes=1))
        self.assertEqual(attempt.status, AttemptStatus.RETRY_SCHEDULED)
        self.assertIsNone(DeliveryFailureQueue.objects.filter(message=message).first())

    def test_permanent_failure_moves_message_to_failed_and_queue(self):
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)
        attempt = MessageQueueService.begin_send_attempt(message=message)

        MessageQueueService.mark_attempt_failed(
            message=message,
            attempt=attempt,
            error_class=ErrorClass.PERMANENT,
            error_code="smtp_rejected",
            error_message="Постоянная ошибка SMTP",
        )
        message.refresh_from_db()
        failure_item = DeliveryFailureQueue.objects.get(message=message)

        self.assertEqual(message.status, MessageStatus.FAILED)
        self.assertFalse(message.requires_manual_retry)
        self.assertEqual(failure_item.failure_type, ErrorClass.PERMANENT)

    def test_exhausted_retries_moves_message_to_manual_retry(self):
        message = self.create_outgoing_message()

        for attempt_number in range(1, MAX_SEND_ATTEMPTS + 1):
            MessageQueueService.enqueue_message(message=message, force=True)
            attempt = MessageQueueService.begin_send_attempt(message=message)
            self.assertEqual(attempt.attempt_number, attempt_number)
            MessageQueueService.mark_attempt_failed(
                message=message,
                attempt=attempt,
                error_class=ErrorClass.TEMPORARY,
                error_code="smtp_timeout",
                error_message="Временная ошибка SMTP",
            )

        message.refresh_from_db()
        failure_item = DeliveryFailureQueue.objects.get(message=message)

        self.assertEqual(message.status, MessageStatus.REQUIRES_MANUAL_RETRY)
        self.assertTrue(message.requires_manual_retry)
        self.assertEqual(failure_item.failure_type, "retry_exhausted")

    def test_successful_attempt_moves_message_to_sent(self):
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)
        attempt = MessageQueueService.begin_send_attempt(message=message)

        MessageQueueService.mark_attempt_succeeded(
            message=message,
            attempt=attempt,
            provider_message_id="provider-1",
            provider_response_payload={"ok": True},
        )
        message.refresh_from_db()
        attempt.refresh_from_db()

        self.assertEqual(message.status, MessageStatus.SENT)
        self.assertEqual(message.provider_message_id, "provider-1")
        self.assertEqual(attempt.status, AttemptStatus.SUCCEEDED)


class TelegramInboundWebhookTests(TestCase):
    def setUp(self):
        self.client_company = Client.objects.create(name="Telegram Co")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Ivan",
            telegram="123456789",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_telegram_webhook",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Telegram Deal",
            client=self.client_company,
            stage=self.stage_active,
        )

    def test_incoming_telegram_message_creates_conversation_message_and_touch(self):
        response = self.client.post(
            "/api/v1/webhooks/telegram/",
            data={
                "update_id": 4001,
                "message": {
                    "message_id": 55,
                    "date": 1710000000,
                    "chat": {"id": "123456789", "type": "private"},
                    "from": {"id": "123456789", "first_name": "Ivan", "username": "ivancrm"},
                    "text": "Здравствуйте, хочу обсудить КП",
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Touch.objects.count(), 1)
        self.assertEqual(MessageWebhookEvent.objects.count(), 1)

        conversation = Conversation.objects.get()
        message = Message.objects.get()
        touch = Touch.objects.get()
        webhook_event = MessageWebhookEvent.objects.get()

        self.assertEqual(conversation.channel, CommunicationChannelCode.TELEGRAM)
        self.assertEqual(conversation.client, self.client_company)
        self.assertEqual(conversation.contact, self.contact)
        self.assertEqual(conversation.deal, self.deal)
        self.assertFalse(conversation.requires_manual_binding)

        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.status, MessageStatus.RECEIVED)
        self.assertEqual(message.direction, MessageDirection.INCOMING)
        self.assertEqual(message.external_message_id, "telegram:123456789:55")
        self.assertEqual(message.body_text, "Здравствуйте, хочу обсудить КП")
        self.assertEqual(message.client, self.client_company)
        self.assertEqual(message.contact, self.contact)
        self.assertEqual(message.deal, self.deal)
        self.assertEqual(message.touch, touch)

        self.assertEqual(touch.summary, "Здравствуйте, хочу обсудить КП")
        self.assertEqual(touch.client, self.client_company)
        self.assertEqual(touch.contact, self.contact)
        self.assertEqual(touch.deal, self.deal)

        self.assertEqual(webhook_event.processing_status, WebhookProcessingStatus.PROCESSED)
        self.assertEqual(webhook_event.external_event_id, "4001")
        self.assertEqual(webhook_event.external_message_id, "telegram:123456789:55")

    def test_duplicate_update_is_ignored_without_duplicate_message_or_touch(self):
        payload = {
            "update_id": 4002,
            "message": {
                "message_id": 56,
                "date": 1710000010,
                "chat": {"id": "123456789", "type": "private"},
                "from": {"id": "123456789", "first_name": "Ivan"},
                "text": "Повторно отправляю сообщение",
            },
        }

        first_response = self.client.post("/api/v1/webhooks/telegram/", data=payload, content_type="application/json")
        second_response = self.client.post("/api/v1/webhooks/telegram/", data=payload, content_type="application/json")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Touch.objects.count(), 1)
        self.assertEqual(MessageWebhookEvent.objects.count(), 1)
        self.assertTrue(second_response.json()["result"]["duplicate"])

    def test_multiple_active_deals_mark_conversation_for_manual_binding(self):
        Deal.objects.create(
            title="Second Deal",
            client=self.client_company,
            stage=self.stage_active,
        )

        response = self.client.post(
            "/api/v1/webhooks/telegram/",
            data={
                "update_id": 4003,
                "message": {
                    "message_id": 57,
                    "date": 1710000020,
                    "chat": {"id": "123456789", "type": "private"},
                    "from": {"id": "123456789", "first_name": "Ivan"},
                    "text": "Есть вопрос по нескольким проектам",
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.get()
        message = Message.objects.get()
        touch = Touch.objects.get()

        self.assertTrue(conversation.requires_manual_binding)
        self.assertIsNone(conversation.deal)
        self.assertIsNone(message.deal)
        self.assertIsNone(touch.deal)
        self.assertEqual(conversation.contact, self.contact)


class TelegramOutboundMessageServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_tg_out",
            password="secret123",
            is_staff=True,
        )
        self.client_company = Client.objects.create(name="Outbound Co")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Oleg",
            telegram="123456789",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_telegram_out",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Outbound Deal",
            client=self.client_company,
            stage=self.stage_active,
            owner=self.user,
        )
        self.conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.TELEGRAM,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
        )
        ConversationBindingService.bind_conversation(
            conversation=self.conversation,
            channel=CommunicationChannelCode.TELEGRAM,
            route_type="telegram_chat",
            route_key="123456789",
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            resolved_by=self.user,
            resolution_source="manual",
        )

    def create_outgoing_message(self) -> Message:
        return Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.TELEGRAM,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="КП отправлено",
            body_text="Отправляю коммерческое предложение",
            body_preview="Отправляю коммерческое предложение",
        )

    @patch("crm_communications.services.send_telegram_chat_message")
    def test_send_message_marks_outgoing_telegram_message_as_sent(self, send_telegram_mock):
        send_telegram_mock.return_value = {"ok": True, "payload": {"result": {"message_id": 777}}}
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)

        processed = TelegramOutboundMessageService.send_message(message=message)
        processed.refresh_from_db()
        self.conversation.refresh_from_db()

        self.assertEqual(processed.status, MessageStatus.SENT)
        self.assertEqual(processed.provider_message_id, "777")
        self.assertEqual(processed.provider_chat_id, "123456789")
        self.assertEqual(processed.external_recipient_key, "telegram:123456789")
        self.assertEqual(processed.attempt_logs.count(), 1)
        self.assertEqual(processed.attempt_logs.first().status, AttemptStatus.SUCCEEDED)
        self.assertEqual(self.conversation.last_message, processed)
        self.assertEqual(self.conversation.last_message_direction, MessageDirection.OUTGOING)
        self.assertIsNotNone(processed.touch_id)
        self.assertEqual(processed.touch.deal, self.deal)
        self.assertEqual(processed.touch.contact, self.contact)
        self.assertIn("КП отправлено", processed.touch.summary)
        send_telegram_mock.assert_called_once()
        self.assertEqual(send_telegram_mock.call_args.kwargs["chat_id"], "123456789")

    def test_send_message_without_numeric_chat_id_moves_to_manual_retry(self):
        self.conversation.routes.all().delete()
        self.contact.telegram = "@oleg"
        self.contact.save(update_fields=["telegram"])
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)

        processed = TelegramOutboundMessageService.send_message(message=message)
        processed.refresh_from_db()

        self.assertEqual(processed.status, MessageStatus.REQUIRES_MANUAL_RETRY)
        self.assertTrue(processed.requires_manual_retry)
        self.assertEqual(processed.last_error_code, "missing_telegram_chat_id")
        self.assertEqual(processed.delivery_failure_queue_item.failure_type, "manual_retry_required")

    @patch("crm_communications.services.send_telegram_chat_message")
    def test_send_due_messages_processes_only_due_queued_messages(self, send_telegram_mock):
        send_telegram_mock.return_value = {"ok": True, "payload": {"result": {"message_id": 778}}}
        due_message = self.create_outgoing_message()
        future_message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=due_message)
        MessageQueueService.enqueue_message(message=future_message)
        future_message.next_attempt_at = timezone.now() + timedelta(hours=1)
        future_message.save(update_fields=["next_attempt_at", "updated_at"])

        result = TelegramOutboundMessageService.send_due_messages(limit=10)
        due_message.refresh_from_db()
        future_message.refresh_from_db()

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(due_message.status, MessageStatus.SENT)
        self.assertEqual(future_message.status, MessageStatus.QUEUED)


class EmailInboundServiceTests(TestCase):
    def setUp(self):
        self.client_company = Client.objects.create(name="Email Co")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Maria",
            email="maria@example.com",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_email_inbound",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Email Deal",
            client=self.client_company,
            stage=self.stage_active,
        )

    def build_email(
        self,
        *,
        message_id: str,
        subject: str,
        body: str,
        references: str = "",
        in_reply_to: str = "",
        attachment_name: str = "",
        attachment_content: bytes | None = None,
    ) -> bytes:
        message = EmailMessage()
        message["From"] = "Maria <maria@example.com>"
        message["To"] = "sales@buyes.pro"
        message["Subject"] = subject
        message["Message-ID"] = f"<{message_id}>"
        message["Date"] = "Fri, 22 Mar 2026 12:00:00 +0600"
        if references:
            message["References"] = references
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        message.set_content(body)
        if attachment_name:
            message.add_attachment(
                attachment_content or b"attachment body",
                maintype="application",
                subtype="octet-stream",
                filename=attachment_name,
            )
        return message.as_bytes()

    def test_process_raw_email_creates_conversation_message_touch(self):
        result = EmailInboundService.process_raw_email(
            raw_message=self.build_email(
                message_id="email-1@example.com",
                subject="Запрос по КП",
                body="Здравствуйте, пришлите актуальное КП.",
            )
        )

        self.assertTrue(result["ok"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Touch.objects.count(), 1)

        conversation = Conversation.objects.get()
        message = Message.objects.get()
        touch = Touch.objects.get()

        self.assertEqual(conversation.channel, CommunicationChannelCode.EMAIL)
        self.assertEqual(conversation.contact, self.contact)
        self.assertEqual(conversation.deal, self.deal)
        self.assertEqual(message.status, MessageStatus.RECEIVED)
        self.assertEqual(message.external_message_id, "email-1@example.com")
        self.assertEqual(message.subject, "Запрос по КП")
        self.assertIn("актуальное КП", message.body_text)
        self.assertEqual(message.touch, touch)
        self.assertEqual(touch.deal, self.deal)
        self.assertIn("актуальное КП", touch.summary)

    def test_duplicate_message_id_is_ignored(self):
        raw_message = self.build_email(
            message_id="email-2@example.com",
            subject="Дубликат",
            body="Проверка дедупликации",
        )
        first_result = EmailInboundService.process_raw_email(raw_message=raw_message)
        second_result = EmailInboundService.process_raw_email(raw_message=raw_message)

        self.assertFalse(first_result["duplicate"])
        self.assertTrue(second_result["duplicate"])
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Touch.objects.count(), 1)

    def test_reply_uses_same_conversation_by_thread(self):
        first = EmailInboundService.process_raw_email(
            raw_message=self.build_email(
                message_id="email-3@example.com",
                subject="Первое письмо",
                body="Начинаем диалог",
            )
        )
        second = EmailInboundService.process_raw_email(
            raw_message=self.build_email(
                message_id="email-4@example.com",
                subject="Re: Первое письмо",
                body="Продолжение диалога",
                references="<email-3@example.com>",
                in_reply_to="<email-3@example.com>",
            )
        )

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(first["conversation_id"], second["conversation_id"])
        self.assertEqual(Message.objects.count(), 2)

    def test_multiple_active_deals_mark_email_conversation_for_manual_binding(self):
        Deal.objects.create(
            title="Second Email Deal",
            client=self.client_company,
            stage=self.stage_active,
        )

        EmailInboundService.process_raw_email(
            raw_message=self.build_email(
                message_id="email-5@example.com",
                subject="Есть вопрос по нескольким сделкам",
                body="Нужно уточнение по двум проектам",
            )
        )

        conversation = Conversation.objects.get()
        message = Message.objects.get()
        touch = Touch.objects.get()

        self.assertTrue(conversation.requires_manual_binding)
        self.assertIsNone(conversation.deal)
        self.assertIsNone(message.deal)
        self.assertIsNone(touch.deal)

    def test_process_raw_email_saves_attachments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                EmailInboundService.process_raw_email(
                    raw_message=self.build_email(
                        message_id="email-6@example.com",
                        subject="Документы",
                        body="Во вложении файл",
                        attachment_name="spec.pdf",
                        attachment_content=b"pdf-content",
                    )
                )

                self.assertEqual(MessageAttachment.objects.count(), 1)
                attachment = MessageAttachment.objects.get()
                self.assertEqual(attachment.original_name, "spec.pdf")
                self.assertEqual(attachment.size_bytes, len(b"pdf-content"))
                self.assertTrue(attachment.file.name.endswith("spec.pdf"))


class EmailOutboundMessageServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_email_out",
            password="secret123",
            is_staff=True,
        )
        self.client_company = Client.objects.create(name="Outbound Email Co", email="info@example.com")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Elena",
            email="elena@example.com",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_email_out",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Email Out Deal",
            client=self.client_company,
            stage=self.stage_active,
            owner=self.user,
        )
        self.conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.EMAIL,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
        )
        ConversationBindingService.bind_conversation(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            route_type="email_thread",
            route_key="thread-root@example.com",
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            resolved_by=self.user,
            resolution_source="manual",
        )
        Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.INCOMING,
            status=MessageStatus.RECEIVED,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            subject="Re: КП",
            body_text="Ждём ответ",
            body_preview="Ждём ответ",
            external_message_id="latest-incoming@example.com",
            received_at=timezone.now() - timedelta(minutes=5),
        )

    def create_outgoing_message(self) -> Message:
        return Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Ответ по КП",
            body_text="Отправляю обновлённое предложение.",
            body_html="<p>Отправляю <b>обновлённое</b> предложение.</p>",
            body_preview="Отправляю обновлённое предложение.",
        )

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_send_message_marks_email_as_sent_and_sets_thread_headers(self, email_cls_mock):
        email_instance = email_cls_mock.return_value
        email_instance.send.return_value = 1
        message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=message)

        processed = EmailOutboundMessageService.send_message(message=message)
        processed.refresh_from_db()
        self.conversation.refresh_from_db()

        self.assertEqual(processed.status, MessageStatus.SENT)
        self.assertTrue(processed.external_message_id)
        self.assertEqual(processed.provider_message_id, processed.external_message_id)
        self.assertEqual(processed.external_recipient_key, "email:elena@example.com")
        self.assertEqual(processed.in_reply_to, "latest-incoming@example.com")
        self.assertEqual(processed.references, "thread-root@example.com latest-incoming@example.com")
        self.assertEqual(processed.attempt_logs.count(), 1)
        self.assertEqual(processed.attempt_logs.first().status, AttemptStatus.SUCCEEDED)
        self.assertEqual(self.conversation.last_message, processed)
        self.assertEqual(self.conversation.last_message_direction, MessageDirection.OUTGOING)
        self.assertIsNotNone(processed.touch_id)
        self.assertEqual(processed.touch.deal, self.deal)
        self.assertEqual(processed.touch.contact, self.contact)
        self.assertIn("Ответ по КП", processed.touch.summary)

        email_cls_mock.assert_called_once()
        _, kwargs = email_cls_mock.call_args
        self.assertEqual(kwargs["headers"]["In-Reply-To"], "<latest-incoming@example.com>")
        self.assertEqual(kwargs["headers"]["References"], "<thread-root@example.com> <latest-incoming@example.com>")
        self.assertEqual(kwargs["to"], ["elena@example.com"])
        email_instance.attach_alternative.assert_called_once()
        email_instance.send.assert_called_once_with(fail_silently=False)

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_send_message_without_recipient_moves_to_manual_retry(self, email_cls_mock):
        self.contact.email = ""
        self.contact.save(update_fields=["email"])
        self.client_company.email = ""
        self.client_company.save(update_fields=["email"])
        message = self.create_outgoing_message()
        message.external_recipient_key = ""
        message.save(update_fields=["external_recipient_key", "updated_at"])
        MessageQueueService.enqueue_message(message=message)

        processed = EmailOutboundMessageService.send_message(message=message)
        processed.refresh_from_db()

        self.assertEqual(processed.status, MessageStatus.REQUIRES_MANUAL_RETRY)
        self.assertTrue(processed.requires_manual_retry)
        self.assertEqual(processed.last_error_code, "missing_email_recipient")
        self.assertEqual(processed.delivery_failure_queue_item.failure_type, "manual_retry_required")
        email_cls_mock.assert_not_called()

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_send_due_messages_processes_only_due_email_messages(self, email_cls_mock):
        email_instance = email_cls_mock.return_value
        email_instance.send.return_value = 1
        due_message = self.create_outgoing_message()
        future_message = self.create_outgoing_message()
        MessageQueueService.enqueue_message(message=due_message)
        MessageQueueService.enqueue_message(message=future_message)
        future_message.next_attempt_at = timezone.now() + timedelta(hours=1)
        future_message.save(update_fields=["next_attempt_at", "updated_at"])

        result = EmailOutboundMessageService.send_due_messages(limit=10)
        due_message.refresh_from_db()
        future_message.refresh_from_db()

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(due_message.status, MessageStatus.SENT)
        self.assertEqual(future_message.status, MessageStatus.QUEUED)


class CommunicationsApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="comm_api_staff",
            password="secret123",
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.client_company = Client.objects.create(name="API Co", email="api@example.com")
        self.contact = Contact.objects.create(
            client=self.client_company,
            first_name="Svetlana",
            email="sveta@example.com",
            telegram="123456789",
        )
        self.stage_active = DealStage.objects.create(
            name="В работе",
            code="in_progress_comm_api",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="API Deal",
            client=self.client_company,
            stage=self.stage_active,
            owner=self.user,
        )
        self.conversation = Conversation.objects.create(
            channel=CommunicationChannelCode.EMAIL,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            subject="Email thread",
        )
        ConversationBindingService.bind_conversation(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            route_type="email_thread",
            route_key="api-thread@example.com",
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            resolved_by=self.user,
            resolution_source="manual",
        )
        self.incoming_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.INCOMING,
            status=MessageStatus.RECEIVED,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            subject="Входящее письмо",
            body_text="Нужен ответ",
            body_preview="Нужен ответ",
            external_message_id="inbound-api@example.com",
            received_at=timezone.now(),
        )

    def test_list_conversations_by_deal(self):
        response = self.client.get(
            reverse("communications-conversations-list"),
            {"deal": self.deal.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], self.conversation.pk)

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_send_message_from_conversation(self, email_cls_mock):
        email_instance = email_cls_mock.return_value
        email_instance.send.return_value = 1

        response = self.client.post(
            reverse("communications-conversations-send", kwargs={"pk": self.conversation.pk}),
            data={"subject": "Ответ", "body_text": "Отправляю ответ клиенту"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        message = Message.objects.get(pk=response.json()["id"])
        self.assertEqual(message.direction, MessageDirection.OUTGOING)
        self.assertEqual(message.status, MessageStatus.SENT)
        email_cls_mock.assert_called_once()

    def test_manual_bind_updates_conversation(self):
        second_deal = Deal.objects.create(
            title="Second API Deal",
            client=self.client_company,
            stage=self.stage_active,
            owner=self.user,
        )
        self.conversation.deal = None
        self.conversation.requires_manual_binding = True
        self.conversation.save(update_fields=["deal", "requires_manual_binding", "updated_at"])

        response = self.client.post(
            reverse("communications-conversations-bind", kwargs={"pk": self.conversation.pk}),
            data={"deal": second_deal.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.deal, second_deal)
        self.assertFalse(self.conversation.requires_manual_binding)

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_retry_failed_message(self, email_cls_mock):
        email_instance = email_cls_mock.return_value
        email_instance.send.return_value = 1
        failed_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Повтор",
            body_text="Новая отправка",
        )
        MessageQueueService.enqueue_message(message=failed_message)
        attempt = MessageQueueService.begin_send_attempt(message=failed_message)
        MessageQueueService.mark_attempt_failed(
            message=failed_message,
            attempt=attempt,
            error_class=ErrorClass.MANUAL_REQUIRED,
            error_code="missing_email_recipient",
            error_message="Не найден email получателя.",
        )

        response = self.client.post(
            reverse("communications-messages-retry", kwargs={"pk": failed_message.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        failed_message.refresh_from_db()
        self.assertEqual(failed_message.status, MessageStatus.SENT)

    def test_attempts_and_failures_endpoints(self):
        failed_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Ошибка доставки",
            body_text="Письмо не ушло",
        )
        MessageQueueService.enqueue_message(message=failed_message)
        attempt = MessageQueueService.begin_send_attempt(message=failed_message)
        MessageQueueService.mark_attempt_failed(
            message=failed_message,
            attempt=attempt,
            error_class=ErrorClass.PERMANENT,
            error_code="smtp_rejected",
            error_message="Постоянная ошибка SMTP",
        )

        attempts_response = self.client.get(reverse("communications-messages-attempts", kwargs={"pk": failed_message.pk}))
        failures_response = self.client.get(reverse("communications-failures-list"))

        self.assertEqual(attempts_response.status_code, 200)
        self.assertEqual(len(attempts_response.json()), 1)
        self.assertEqual(failures_response.status_code, 200)
        self.assertEqual(failures_response.json()["results"][0]["message"], failed_message.pk)

    @patch("crm_communications.email_outbound.EmailMultiAlternatives")
    def test_retry_failure_item_retries_message_and_marks_item_resolved(self, email_cls_mock):
        email_instance = email_cls_mock.return_value
        email_instance.send.return_value = 1
        failed_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Ошибка доставки",
            body_text="Нужен ручной повтор",
        )
        MessageQueueService.enqueue_message(message=failed_message)
        attempt = MessageQueueService.begin_send_attempt(message=failed_message)
        MessageQueueService.mark_attempt_failed(
            message=failed_message,
            attempt=attempt,
            error_class=ErrorClass.MANUAL_REQUIRED,
            error_code="missing_email_recipient",
            error_message="Не найден получатель.",
        )
        failure_item = DeliveryFailureQueue.objects.get(message=failed_message)

        response = self.client.post(
            reverse("communications-failures-retry", kwargs={"pk": failure_item.pk}),
            data={"recipient": "email:sveta@example.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        failed_message.refresh_from_db()
        failure_item.refresh_from_db()
        self.assertEqual(failed_message.status, MessageStatus.SENT)
        self.assertEqual(failed_message.external_recipient_key, "email:sveta@example.com")
        self.assertEqual(failure_item.resolution_status, "resolved")
        self.assertEqual(failure_item.assigned_to, self.user)

    def test_bind_failure_item_updates_conversation_message_and_touch_context(self):
        second_deal = Deal.objects.create(
            title="Second bind target",
            client=self.client_company,
            stage=self.stage_active,
            owner=self.user,
        )
        failed_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=None,
            author_user=self.user,
            subject="Нужна перепривязка",
            body_text="Уточнить, к какой сделке относится письмо",
        )
        failed_message.touch = Touch.objects.create(
            happened_at=timezone.now(),
            direction="outgoing",
            summary="Письмо без сделки",
            client=self.client_company,
            contact=self.contact,
        )
        failed_message.save(update_fields=["touch", "updated_at"])
        self.conversation.deal = None
        self.conversation.requires_manual_binding = True
        self.conversation.save(update_fields=["deal", "requires_manual_binding", "updated_at"])
        MessageQueueService.enqueue_message(message=failed_message)
        attempt = MessageQueueService.begin_send_attempt(message=failed_message)
        MessageQueueService.mark_attempt_failed(
            message=failed_message,
            attempt=attempt,
            error_class=ErrorClass.PERMANENT,
            error_code="smtp_rejected",
            error_message="Нужна ручная проверка.",
        )
        failure_item = DeliveryFailureQueue.objects.get(message=failed_message)

        response = self.client.post(
            reverse("communications-failures-bind", kwargs={"pk": failure_item.pk}),
            data={"deal": second_deal.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.conversation.refresh_from_db()
        failed_message.refresh_from_db()
        failure_item.refresh_from_db()
        failed_message.touch.refresh_from_db()
        self.assertEqual(self.conversation.deal, second_deal)
        self.assertFalse(self.conversation.requires_manual_binding)
        self.assertEqual(failed_message.deal, second_deal)
        self.assertEqual(failed_message.touch.deal, second_deal)
        self.assertEqual(failure_item.resolution_status, "in_progress")
        self.assertEqual(failure_item.assigned_to, self.user)

    def test_resolve_and_close_failure_item(self):
        failed_message = Message.objects.create(
            conversation=self.conversation,
            channel=CommunicationChannelCode.EMAIL,
            direction=MessageDirection.OUTGOING,
            status=MessageStatus.DRAFT,
            client=self.client_company,
            contact=self.contact,
            deal=self.deal,
            author_user=self.user,
            subject="Ошибка",
            body_text="Требуется ручная обработка",
        )
        MessageQueueService.enqueue_message(message=failed_message)
        attempt = MessageQueueService.begin_send_attempt(message=failed_message)
        MessageQueueService.mark_attempt_failed(
            message=failed_message,
            attempt=attempt,
            error_class=ErrorClass.PERMANENT,
            error_code="smtp_rejected",
            error_message="Письмо отклонено.",
        )
        failure_item = DeliveryFailureQueue.objects.get(message=failed_message)

        resolve_response = self.client.post(
            reverse("communications-failures-resolve", kwargs={"pk": failure_item.pk}),
            data={"resolution_comment": "Исправлено вручную вне CRM."},
            content_type="application/json",
        )
        self.assertEqual(resolve_response.status_code, 200)
        failure_item.refresh_from_db()
        self.assertEqual(failure_item.resolution_status, "resolved")
        self.assertEqual(failure_item.resolution_comment, "Исправлено вручную вне CRM.")
        self.assertEqual(failure_item.assigned_to, self.user)

        close_response = self.client.post(
            reverse("communications-failures-close", kwargs={"pk": failure_item.pk}),
            data={"resolution_comment": "Закрыто без повтора."},
            content_type="application/json",
        )
        self.assertEqual(close_response.status_code, 200)
        failure_item.refresh_from_db()
        self.assertEqual(failure_item.resolution_status, "closed")
        self.assertEqual(failure_item.resolution_comment, "Закрыто без повтора.")


class CommunicationsOpsCommandTests(TestCase):
    @patch("crm_communications.management.commands.process_communications_outbox.TelegramOutboundMessageService.send_due_messages")
    @patch("crm_communications.management.commands.process_communications_outbox.EmailOutboundMessageService.send_due_messages")
    def test_process_outbox_runs_both_channels_and_prints_summary(self, email_mock, telegram_mock):
        email_mock.return_value = {"processed": 2, "sent": 1, "failed": 1, "manual_retry": 0, "message_ids": [1, 2]}
        telegram_mock.return_value = {"processed": 1, "sent": 1, "failed": 0, "manual_retry": 0, "message_ids": [3]}
        stdout = StringIO()

        call_command("process_communications_outbox", limit=25, stdout=stdout)

        output = stdout.getvalue()
        email_mock.assert_called_once_with(limit=25)
        telegram_mock.assert_called_once_with(limit=25)
        self.assertIn("email: processed=2 sent=1 failed=1 manual_retry=0", output)
        self.assertIn("telegram: processed=1 sent=1 failed=0 manual_retry=0", output)
        self.assertIn("done: processed=3 sent=2 failed=1 manual_retry=0", output)

    @patch("crm_communications.management.commands.process_communications_outbox.TelegramOutboundMessageService.send_due_messages")
    @patch("crm_communications.management.commands.process_communications_outbox.EmailOutboundMessageService.send_due_messages")
    def test_process_outbox_respects_email_only_flag(self, email_mock, telegram_mock):
        email_mock.return_value = {"processed": 1, "sent": 1, "failed": 0, "manual_retry": 0, "message_ids": [1]}
        stdout = StringIO()

        call_command("process_communications_outbox", email_only=True, stdout=stdout)

        email_mock.assert_called_once()
        telegram_mock.assert_not_called()

    @patch("crm_communications.management.commands.fetch_imap_inbox.build_imap_poller_from_settings")
    def test_fetch_imap_inbox_command_runs_poller(self, build_poller_mock):
        class DummyPoller:
            host = "imap.beget.com"
            username = "crm@example.com"
            password = "secret"

            def poll(self, *, limit, search_criteria):
                return {
                    "processed": limit,
                    "duplicates": 1,
                    "mailbox": "INBOX",
                    "search_criteria": search_criteria,
                }

        build_poller_mock.return_value = DummyPoller()
        stdout = StringIO()

        call_command("fetch_imap_inbox", limit=7, search="UNSEEN", stdout=stdout)

        output = stdout.getvalue()
        build_poller_mock.assert_called_once()
        self.assertIn("Processed=7 duplicates=1 mailbox=INBOX", output)

    @patch("crm_communications.management.commands.fetch_imap_inbox.build_imap_poller_from_settings")
    def test_fetch_imap_inbox_command_requires_imap_settings(self, build_poller_mock):
        class DummyPoller:
            host = ""
            username = ""
            password = ""

            def poll(self, *, limit, search_criteria):
                raise AssertionError("poll should not be called")

        build_poller_mock.return_value = DummyPoller()

        with self.assertRaisesMessage(CommandError, "IMAP не настроен. Проверьте IMAP_HOST / IMAP_USER / IMAP_PASSWORD."):
            call_command("fetch_imap_inbox")
