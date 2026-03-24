from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta

from crm.models import Activity, Client, ClientDocument, CommunicationChannel, Contact, Deal, DealDocument, DealStage, Lead, LeadStatus, Touch, TouchResult
from crm.models.activity import ActivityType


class TouchesApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_touch",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.channel = CommunicationChannel.objects.create(name="Телефон")
        self.lead_status = LeadStatus.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.touch_result = TouchResult.objects.create(
            name="Назначен следующий шаг",
            group="follow_up",
            result_class="neutral",
            requires_next_step=True,
            allowed_touch_types=["call"],
            sort_order=10,
        )
        self.company = Client.objects.create(name="Acme")
        self.contact = Contact.objects.create(client=self.company, first_name="Иван", last_name="Иванов")
        self.lead = Lead.objects.create(title="Лид для касания", company="Acme", status=self.lead_status)
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.channel.touch_results.add(self.touch_result)
        self.lead_status.touch_results.add(self.touch_result)
        self.stage.touch_results.add(self.touch_result)
        self.deal = Deal.objects.create(title="Сделка для касания", stage=self.stage, client=self.company)
        self.task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Задача для касания",
            due_at=timezone.now() + timedelta(days=1),
        )

    def test_cannot_create_touch_without_link(self):
        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "direction": "incoming",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lead", response.data)

    def test_can_create_touch_for_deal(self):
        happened_at = timezone.now() - timedelta(hours=1)
        next_step_at = timezone.now() + timedelta(days=1)
        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": happened_at.isoformat(),
                "channel": self.channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Обсудили условия поставки",
                "next_step": "Подготовить КП",
                "next_step_at": next_step_at.isoformat(),
                "owner": self.user.pk,
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["channel_name"], "Телефон")
        self.assertEqual(response.data["result_option_name"], "Назначен следующий шаг")
        self.assertEqual(response.data["result_option_group"], "follow_up")
        self.assertEqual(response.data["result_option_class"], "neutral")
        self.assertEqual(response.data["direction_label"], "Исходящее")
        self.assertEqual(response.data["deal_title"], "Сделка для касания")

        touch = Touch.objects.get(pk=response.data["id"])
        self.assertEqual(touch.summary, "Обсудили условия поставки")

    def test_can_create_touch_for_lead(self):
        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "direction": "incoming",
                "summary": "Входящий запрос",
                "lead": self.lead.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["lead_title"], "Лид для касания")

    def test_can_create_touch_with_company_contact_and_task(self):
        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "direction": "incoming",
                "summary": "Связались через контакт",
                "client": self.company.pk,
                "contact": self.contact.pk,
                "task": self.task.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["client_name"], "Acme")
        self.assertEqual(response.data["contact_name"], "Иван Иванов")
        self.assertEqual(response.data["task_subject"], "Задача для касания")

    def test_touch_result_meta_returns_structured_fields(self):
        response = self.client.get(reverse("meta-touch-results"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["code"], self.touch_result.code)
        self.assertEqual(response.data[0]["group"], "follow_up")
        self.assertEqual(response.data[0]["class"], "neutral")
        self.assertEqual(response.data[0]["requires_next_step"], True)
        self.assertEqual(response.data[0]["allowed_touch_types"], ["call"])
        self.assertNotIn("lead_status_ids", response.data[0])
        self.assertNotIn("deal_stage_ids", response.data[0])

    def test_communication_channel_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-communication-channels"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        channel_payload = next(item for item in response.data if item["id"] == self.channel.pk)
        self.assertEqual(channel_payload["touch_result_ids"], [self.touch_result.pk])

    def test_lead_status_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-lead-statuses"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["touch_result_ids"], [self.touch_result.pk])

    def test_deal_stage_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-deal-stages"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["touch_result_ids"], [self.touch_result.pk])

    def test_cannot_use_touch_result_with_unsupported_channel(self):
        email_channel = CommunicationChannel.objects.create(name="Email")

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "channel": email_channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Письмо отправлено",
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("result_option", response.data)

    def test_channel_touch_results_do_not_block_manual_save(self):
        restricted_channel = CommunicationChannel.objects.create(name="Telegram")
        allowed_channel_result = TouchResult.objects.create(
            name="Только для фильтра канала",
            group="follow_up",
            result_class="neutral",
            requires_next_step=False,
            allowed_touch_types=[],
            sort_order=20,
        )
        manual_result = TouchResult.objects.create(
            name="Ручной результат вне канала",
            group="follow_up",
            result_class="neutral",
            requires_next_step=False,
            allowed_touch_types=[],
            sort_order=21,
        )
        restricted_channel.touch_results.add(allowed_channel_result)

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "channel": restricted_channel.pk,
                "result_option": manual_result.pk,
                "direction": "outgoing",
                "summary": "Сообщение вручную сохранено",
                "next_step_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["result_option_name"], manual_result.name)

    def test_can_attach_company_and_deal_documents_to_touch(self):
        company_document = ClientDocument.objects.create(
            client=self.company,
            file=SimpleUploadedFile("company.txt", b"company", content_type="text/plain"),
            original_name="company.txt",
        )
        deal_document = DealDocument.objects.create(
            deal=self.deal,
            file=SimpleUploadedFile("deal.txt", b"deal", content_type="text/plain"),
            original_name="deal.txt",
        )

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": timezone.now().isoformat(),
                "direction": "incoming",
                "summary": "Отправили документы",
                "next_step_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "client": self.company.pk,
                "deal": self.deal.pk,
                "client_document_ids": [company_document.pk],
                "deal_document_ids": [deal_document.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["client_documents"]), 1)
        self.assertEqual(len(response.data["deal_documents"]), 1)

        touch = Touch.objects.get(pk=response.data["id"])
        self.assertEqual(touch.client_documents.count(), 1)
        self.assertEqual(touch.deal_documents.count(), 1)
        self.deal.refresh_from_db()
        self.company.refresh_from_db()
        self.assertIn("touch_id:", self.deal.events)
        self.assertIn("document_name: company.txt", self.company.events)
        self.assertIn("document_name: deal.txt", self.deal.events)
        self.assertIn(reverse("deal-documents-download", kwargs={"pk": deal_document.pk}), self.deal.events)
        self.assertIn(reverse("client-documents-download", kwargs={"pk": company_document.pk}), self.company.events)
