import tempfile

from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from crm.models import Activity, ClientDocument, Deal, DealStage, Lead, LeadDocument, LeadStatus, Touch
from crm.models.activity import ActivityType, TaskStatus
from crm.models.touch import TouchDirection


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

    def test_converted_deal_receives_lead_events_and_history(self):
        lead = Lead.objects.create(
            title="Lead with history",
            company="Acme",
            status=self.in_progress_status,
            assigned_to=self.user,
            events=(
                "19.03.2026 10:00\n"
                "Результат: Лид квалифицирован\n"
                "event_type: system\n"
                "priority: low\n"
                "title: Системное событие"
            ),
            history=[
                {
                    "event": "chat_opened",
                    "timestamp": timezone.now().isoformat(),
                }
            ],
        )

        lead.status = self.converted_status
        lead.save(update_fields=["status", "updated_at"])

        deal = Deal.objects.get(lead=lead)
        self.assertIn("Лид квалифицирован", deal.events)
        self.assertIn("Открытие чата", deal.events)

    def test_task_and_touch_are_written_to_lead_events(self):
        lead = Lead.objects.create(
            title="Lead events",
            company="Acme",
            status=self.in_progress_status,
            assigned_to=self.user,
        )

        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Позвонить клиенту",
            lead=lead,
            created_by=self.user,
        )
        task.status = TaskStatus.DONE
        task.result = "Созвонились и договорились о демонстрации"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "result", "completed_at", "updated_at"])
        Touch.objects.create(
            happened_at=timezone.now(),
            direction=TouchDirection.OUTGOING,
            summary="Обсудили следующие шаги",
            lead=lead,
            owner=self.user,
        )

        lead.refresh_from_db()
        self.assertIn("Создана задача: Позвонить клиенту", lead.events)
        self.assertIn("Касание: Обсудили следующие шаги", lead.events)

    def test_converted_lead_documents_are_copied_to_company_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                lead = Lead.objects.create(
                    title="Lead with document",
                    company="Acme",
                    status=self.in_progress_status,
                    assigned_to=self.user,
                )
                document = LeadDocument.objects.create(
                    lead=lead,
                    original_name="brief.pdf",
                    uploaded_by=self.user,
                )
                document.file.save("brief.pdf", ContentFile(b"lead-doc-content"), save=True)

                lead.status = self.converted_status
                lead.save(update_fields=["status", "updated_at"])

                company_documents = ClientDocument.objects.filter(client=lead.client)
                self.assertEqual(company_documents.count(), 1)
                company_document = company_documents.first()
                self.assertEqual(company_document.original_name, "brief.pdf")
                self.assertEqual(company_document.uploaded_by, self.user)
                self.assertTrue(company_document.file.name.endswith("brief.pdf"))
