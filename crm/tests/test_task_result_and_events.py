from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Activity, Client, Deal, DealStage
from crm.models.activity import ActivityType


class TaskResultAndEventsTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_events",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(name="Acme")
        self.stage_new = DealStage.objects.create(
            name="Первичный контакт",
            code="primary_contact",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.stage_won = DealStage.objects.create(
            name="Успешно реализовано",
            code="won",
            order=90,
            is_active=True,
            is_final=True,
        )
        self.deal = Deal.objects.create(
            title="Сделка Acme",
            client=self.company,
            stage=self.stage_new,
        )

    def test_task_completion_requires_result_and_writes_events(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
        )

        bad_response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {"is_done": True},
            format="json",
        )
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("result", bad_response.data)

        good_response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {"is_done": True, "result": "Коммерческое предложение отправлено клиенту"},
            format="json",
        )
        self.assertEqual(good_response.status_code, status.HTTP_200_OK)

        task.refresh_from_db()
        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        self.assertTrue(task.is_done)
        self.assertEqual(task.result, "Коммерческое предложение отправлено клиенту")
        self.assertIsNotNone(task.completed_at)
        self.assertIn("Результат: Коммерческое предложение отправлено клиенту", self.deal.events)
        self.assertIn(f"task_id: {task.pk}", self.deal.events)
        self.assertIn(f"deal_id: {self.deal.pk}", self.deal.events)
        self.assertIn("Коммерческое предложение отправлено клиенту", self.company.events)

    def test_deal_completion_writes_events_to_deal_and_company(self):
        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": self.deal.pk}),
            {"stage": self.stage_won.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        self.assertTrue(self.deal.is_won)
        self.assertIn("Результат: Сделка завершена", self.deal.events)
        self.assertIn(f"deal_id: {self.deal.pk}", self.deal.events)
        self.assertIn("Сделка завершена", self.company.events)
        self.assertIn("Успешно реализовано", self.company.events)
