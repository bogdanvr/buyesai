from django.contrib.auth import get_user_model
from django.test import TestCase

from crm.models import Deal, DealStage, Lead, LeadStatus


class LeadAutoConvertSignalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="manager",
            email="manager@example.com",
            password="test-pass-123",
        )
        self.converted_status, _ = LeadStatus.objects.get_or_create(
            code="converted",
            defaults={
                "name": "Converted",
                "order": 10,
                "is_active": True,
                "is_final": True,
            },
        )
        self.in_progress_status, _ = LeadStatus.objects.get_or_create(
            code="in_progress",
            defaults={
                "name": "In progress",
                "order": 20,
                "is_active": True,
                "is_final": False,
            },
        )

    def test_creates_deal_when_lead_created_as_converted(self):
        lead = Lead.objects.create(
            title="Converted lead",
            company="Acme",
            status=self.converted_status,
            assigned_to=self.user,
        )

        lead_deals = Deal.objects.filter(lead=lead)
        self.assertEqual(lead_deals.count(), 1)
        deal = lead_deals.first()
        self.assertEqual(deal.client.name, "Acme")
        self.assertEqual(deal.owner, self.user)
        self.assertIsNotNone(lead.converted_at)

    def test_creates_only_one_deal_when_status_changes_to_converted(self):
        lead = Lead.objects.create(
            title="Lead to convert",
            company="Beta",
            status=self.in_progress_status,
            assigned_to=self.user,
        )
        self.assertFalse(Deal.objects.filter(lead=lead).exists())

        lead.status = self.converted_status
        lead.save(update_fields=["status", "updated_at"])
        self.assertEqual(Deal.objects.filter(lead=lead).count(), 1)

        lead.title = "Lead to convert updated"
        lead.save(update_fields=["title", "updated_at"])
        self.assertEqual(Deal.objects.filter(lead=lead).count(), 1)

    def test_creates_deal_without_client_when_company_is_unknown(self):
        lead = Lead.objects.create(
            title="Lead without company",
            company="",
            status=self.converted_status,
            assigned_to=self.user,
        )

        lead_deals = Deal.objects.filter(lead=lead)
        self.assertEqual(lead_deals.count(), 1)
        deal = lead_deals.first()
        self.assertIsNone(deal.client)
        self.assertIsNone(lead.client)

    def test_prefers_non_final_stage_on_auto_conversion(self):
        final_stage = DealStage.objects.create(
            name="Успешно реализовано",
            code="won",
            order=20,
            is_active=True,
            is_final=True,
        )
        work_stage = DealStage.objects.create(
            name="Новая сделка",
            code="new",
            order=10,
            is_active=True,
            is_final=False,
        )

        lead = Lead.objects.create(
            title="Lead with stage",
            company="Acme",
            status=self.converted_status,
            assigned_to=self.user,
        )

        deal = Deal.objects.get(lead=lead)
        self.assertEqual(deal.stage, work_stage)
        self.assertNotEqual(deal.stage, final_stage)
