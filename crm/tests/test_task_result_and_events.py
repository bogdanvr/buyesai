from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
import re

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
        self.stage_failed = DealStage.objects.create(
            name="Провален",
            code="failed",
            order=100,
            is_active=True,
            is_final=True,
        )
        self.deal = Deal.objects.create(
            title="Сделка Acme",
            client=self.company,
            stage=self.stage_new,
        )

    def test_task_completion_requires_result_and_writes_events_to_deal_and_company(self):
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

    def test_task_completion_can_append_company_note(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
            save_company_note=True,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Коммерческое предложение отправлено клиенту",
                "save_company_note": True,
                "company_note": "Компания работает только по постоплате",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task.refresh_from_db()
        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        self.assertTrue(task.save_company_note)
        self.assertEqual(task.company_note, "Компания работает только по постоплате")
        self.assertIn("Коммерческое предложение отправлено клиенту", self.company.events)
        self.assertIn("Коммерческое предложение отправлено клиенту", self.deal.events)
        self.assertRegex(self.company.notes, r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}")
        self.assertIn("Добавил: staff_events", self.company.notes)
        self.assertIn(f"Сделка #{self.deal.pk}", self.company.notes)
        self.assertIn("Компания работает только по постоплате", self.company.notes)

    def test_task_company_note_requires_text(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "save_company_note": True,
                "company_note": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company_note", response.data)

    def test_active_deal_task_completion_requires_follow_up(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Созвон с клиентом",
            deal=self.deal,
            client=self.company,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Созвон завершён",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("has_follow_up_task", response.data)

    def test_active_deal_task_completion_allows_follow_up(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Созвон с клиентом",
            deal=self.deal,
            client=self.company,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Созвон завершён",
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_company_note_draft_writes_author_and_timestamp(self):
        response = self.client.patch(
            reverse("clients-detail", kwargs={"pk": self.company.pk}),
            {"note_draft": "Любят общаться в Telegram"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        self.assertRegex(self.company.notes, r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}")
        self.assertIn("Добавил: staff_events", self.company.notes)
        self.assertIn("Любят общаться в Telegram", self.company.notes)

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
        self.assertIn("Результат: Статус сделки изменён: Первичный контакт -> Успешно реализовано", self.deal.events)
        self.assertIn("Результат: Сделка завершена", self.deal.events)
        self.assertIn(f"deal_id: {self.deal.pk}", self.deal.events)
        self.assertIn("Сделка завершена", self.company.events)
        self.assertIn("Успешно реализовано", self.company.events)

    def test_deal_stage_change_writes_event_to_deal(self):
        stage_progress = DealStage.objects.create(
            name="Переговоры",
            code="negotiation",
            order=20,
            is_active=True,
            is_final=False,
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": self.deal.pk}),
            {"stage": stage_progress.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        self.assertIn("Результат: Статус сделки изменён: Первичный контакт -> Переговоры", self.deal.events)
        self.assertIn(f"deal_id: {self.deal.pk}", self.deal.events)
        self.assertNotIn("Статус сделки изменён", self.company.events)

    def test_failed_deal_requires_reason(self):
        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": self.deal.pk}),
            {"stage": self.stage_failed.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("failure_reason", response.data)

    def test_failed_deal_reason_writes_events_to_deal_and_company(self):
        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": self.deal.pk}),
            {
                "stage": self.stage_failed.pk,
                "failure_reason": "Клиент выбрал конкурента",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        self.assertEqual(self.deal.metadata.get("failed_reason"), "Клиент выбрал конкурента")
        self.assertIn("Результат: Статус сделки изменён: Первичный контакт -> Провален", self.deal.events)
        self.assertIn("Результат: Сделка провалена. Причина: Клиент выбрал конкурента", self.deal.events)
        self.assertIn("Сделка провалена. Причина: Клиент выбрал конкурента", self.company.events)
