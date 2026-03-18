from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Activity, Client, Deal, DealStage, LeadSource
from crm.models.activity import ActivityType


class DealTasksRequiredByStageTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_deal_tasks",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(name="Acme")
        self.source = LeadSource.objects.create(name="Сайт", code="site")
        self.stage_in_progress = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.stage_failed = DealStage.objects.create(
            name="Провален",
            code="failed",
            order=100,
            is_active=True,
            is_final=True,
        )
        self.stage_thinking = DealStage.objects.create(
            name="Думают",
            code="thinking",
            order=20,
            is_active=True,
            is_final=False,
        )

    def test_cannot_create_non_final_deal_without_tasks(self):
        response = self.client.post(
            reverse("deals-list"),
            {
                "title": "Сделка без задач",
                "source": self.source.pk,
                "client": self.company.pk,
                "stage": self.stage_in_progress.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", response.data)

    def test_can_create_non_final_deal_when_task_is_pending(self):
        response = self.client.post(
            reverse("deals-list"),
            {
                "title": "Сделка с черновиком задачи",
                "source": self.source.pk,
                "client": self.company.pk,
                "stage": self.stage_in_progress.pk,
                "has_pending_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_update_non_final_deal_without_tasks(self):
        deal = Deal.objects.create(
            title="Сделка без задач",
            source=self.source,
            client=self.company,
            stage=self.stage_in_progress,
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"description": "Обновление без задач"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", response.data)

    def test_can_update_non_final_deal_with_existing_task(self):
        deal = Deal.objects.create(
            title="Сделка с задачей",
            source=self.source,
            client=self.company,
            stage=self.stage_in_progress,
        )
        Activity.objects.create(
            type=ActivityType.TASK,
            subject="Перезвонить клиенту",
            deal=deal,
            client=self.company,
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"description": "Обновление с задачей"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_update_non_final_deal_with_only_completed_tasks(self):
        deal = Deal.objects.create(
            title="Сделка с завершенной задачей",
            source=self.source,
            client=self.company,
            stage=self.stage_in_progress,
        )
        Activity.objects.create(
            type=ActivityType.TASK,
            subject="Перезвонить клиенту",
            deal=deal,
            client=self.company,
            is_done=True,
            result="Клиент ответил",
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"description": "Обновление без активных задач"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", response.data)

    def test_can_update_deal_without_tasks_to_failed_stage(self):
        deal = Deal.objects.create(
            title="Сделка без задач",
            source=self.source,
            client=self.company,
            stage=self.stage_in_progress,
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"stage": self.stage_failed.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_create_thinking_deal_without_company(self):
        response = self.client.post(
            reverse("deals-list"),
            {
                "title": "Сделка без компании",
                "source": self.source.pk,
                "stage": self.stage_thinking.pk,
                "has_pending_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("client", response.data)

    def test_can_create_thinking_deal_with_company(self):
        response = self.client.post(
            reverse("deals-list"),
            {
                "title": "Сделка с компанией",
                "source": self.source.pk,
                "client": self.company.pk,
                "stage": self.stage_thinking.pk,
                "has_pending_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
