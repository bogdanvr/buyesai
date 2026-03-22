from django.contrib.auth import get_user_model
from django.test import TestCase

from crm.models import Client, Contact, Deal, DealStage
from crm_communications.models import CommunicationChannelCode, Conversation
from crm_communications.services import (
    ConversationBindingService,
    ConversationResolverService,
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
