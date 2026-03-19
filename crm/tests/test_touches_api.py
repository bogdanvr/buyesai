from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta

from crm.models import Activity, Client, CommunicationChannel, Contact, Deal, DealStage, Lead, Touch, TouchResult
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
        self.touch_result = TouchResult.objects.create(name="Назначен следующий шаг")
        self.company = Client.objects.create(name="Acme")
        self.contact = Contact.objects.create(client=self.company, first_name="Иван", last_name="Иванов")
        self.lead = Lead.objects.create(title="Лид для касания", company="Acme")
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
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
        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "channel": self.channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Обсудили условия поставки",
                "next_step": "Подготовить КП",
                "next_step_at": "2026-03-19T12:00:00+06:00",
                "owner": self.user.pk,
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["channel_name"], "Телефон")
        self.assertEqual(response.data["result_option_name"], "Назначен следующий шаг")
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
