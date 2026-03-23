from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
import re
from datetime import timedelta

from crm.models import (
    Activity,
    Client,
    CommunicationChannel,
    Deal,
    DealStage,
    LeadSource,
    TaskCategory,
    TaskType,
    Touch,
    UserRole,
    UserRoleAssignment,
)
from crm.models.activity import ActivityType, TaskStatus, TaskTypeGroup


class TaskResultAndEventsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_events",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="Acme")
        self.source = LeadSource.objects.create(name="Сайт", code="site")
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
            source=self.source,
            stage=self.stage_new,
        )

    def test_task_completion_requires_result_and_writes_events_to_deal_and_company(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        bad_response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {"is_done": True},
            format="json",
        )
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("result", bad_response.data)
        self.assertEqual(
            bad_response.data["result"][0],
            "Укажите результат выполнения задачи или задайте его в типе задачи.",
        )

        good_response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Коммерческое предложение отправлено клиенту",
                "has_follow_up_task": True,
            },
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

    def test_task_completion_requires_result_even_with_related_touch(self):
        related_touch = Activity.objects.create(
            type=ActivityType.CALL,
            subject="Созвон с клиентом",
            deal=self.deal,
            client=self.company,
            created_by=self.user,
        )
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Зафиксировать итог созвона",
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "related_touch": related_touch.pk,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["result"][0],
            "Укажите результат выполнения задачи или задайте его в типе задачи.",
        )

    def test_client_task_completion_creates_touch(self):
        task_type = TaskType.objects.create(
            name="Созвон с клиентом",
            group=TaskTypeGroup.CLIENT_TASK,
            auto_touch_on_done=True,
            touch_result="Связались повторно",
        )
        channel = CommunicationChannel.objects.create(name="Телефон")
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Обсудить предложение",
            task_type=task_type,
            communication_channel=channel,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task.refresh_from_db()
        touch = Touch.objects.get(task=task)
        self.assertTrue(task.is_done)
        self.assertEqual(task.result, "Связались повторно")
        self.assertEqual(touch.deal_id, self.deal.pk)
        self.assertEqual(touch.client_id, self.company.pk)
        self.assertEqual(touch.channel_id, channel.pk)
        self.assertEqual(touch.result_option.name, "Связались повторно")
        self.assertEqual(touch.summary, "")
        self.assertEqual(touch.next_step, "")

    def test_client_task_completion_requires_communication_channel(self):
        task_type = TaskType.objects.create(
            name="Созвон с клиентом",
            group=TaskTypeGroup.CLIENT_TASK,
            auto_touch_on_done=True,
            touch_result="Связались повторно",
        )
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Обсудить предложение",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["communication_channel"][0],
            "Укажите тип канала перед завершением клиентской задачи.",
        )

    def test_client_task_without_auto_touch_does_not_create_touch(self):
        task_type = TaskType.objects.create(
            name="Написать клиенту",
            group=TaskTypeGroup.CLIENT_TASK,
            auto_touch_on_done=False,
            touch_result="Написали клиенту",
        )
        channel = CommunicationChannel.objects.create(name="Email")
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Написать клиенту",
            task_type=task_type,
            communication_channel=channel,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Touch.objects.filter(task=task).exists())

    def test_internal_task_completion_requires_result(self):
        task_type = TaskType.objects.create(name="Подготовить договор", group=TaskTypeGroup.INTERNAL_TASK)
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить договор",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["result"][0], "Укажите результат выполнения задачи или задайте его в типе задачи.")

    def test_task_completion_uses_result_from_task_type(self):
        task_type = TaskType.objects.create(
            name="Подготовить договор",
            group=TaskTypeGroup.INTERNAL_TASK,
            touch_result="Договор подготовлен",
        )
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить договор",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.result, "Договор подготовлен")

    def test_client_task_completion_writes_client_task_event_type(self):
        task_type = TaskType.objects.create(name="Отправить письмо", group=TaskTypeGroup.CLIENT_TASK)
        channel = CommunicationChannel.objects.create(name="Email")
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить письмо",
            task_type=task_type,
            communication_channel=channel,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Письмо отправлено",
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.deal.refresh_from_db()
        self.assertIn("event_type: client_task_completed_email", self.deal.events)

    def test_internal_task_completion_writes_internal_task_event_type(self):
        task_type = TaskType.objects.create(name="Подготовить договор", group=TaskTypeGroup.INTERNAL_TASK)
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить договор",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Договор подготовлен",
                "has_follow_up_task": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.deal.refresh_from_db()
        self.assertIn("event_type: internal_task_completed", self.deal.events)

    def test_internal_task_completion_requires_follow_up(self):
        task_type = TaskType.objects.create(name="Сверка данных", group=TaskTypeGroup.INTERNAL_TASK)
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Сверить данные",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Данные сверены",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["has_follow_up_task"][0],
            "Для внутренней задачи заполните следующую задачу перед завершением текущей.",
        )

    def test_task_completion_allows_non_overdue_client_task_on_deal(self):
        internal_task_type = TaskType.objects.create(name="Подготовить договор", group=TaskTypeGroup.INTERNAL_TASK)
        client_task_type = TaskType.objects.create(name="Созвон с клиентом", group=TaskTypeGroup.CLIENT_TASK)
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить договор",
            task_type=internal_task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )
        Activity.objects.create(
            type=ActivityType.TASK,
            subject="Созвон с клиентом",
            task_type=client_task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=2),
            status=TaskStatus.IN_PROGRESS,
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Договор подготовлен",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_task_completion_can_append_company_note(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
            save_company_note=True,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Коммерческое предложение отправлено клиенту",
                "has_follow_up_task": True,
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
        self.assertRegex(self.company.notes, r"\d{2}\.\d{2}\.\d{4}")
        self.assertIn("Добавил: staff_events", self.company.notes)
        self.assertIn(f"Сделка #{self.deal.pk}", self.company.notes)
        self.assertIn("Компания работает только по постоплате", self.company.notes)

    def test_task_company_note_requires_text(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Отправить КП",
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
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
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
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
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
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

    def test_task_can_store_type_priority_related_touch_and_status(self):
        task_type = TaskType.objects.create(name="Квалификация", group=TaskTypeGroup.INTERNAL_TASK)
        channel = CommunicationChannel.objects.create(name="Email")
        touch = Activity.objects.create(
            type=ActivityType.CALL,
            subject="Первичный звонок",
            deal=self.deal,
            client=self.company,
        )

        response = self.client.post(
            reverse("activities-list"),
            {
                "type": ActivityType.TASK,
                "subject": "Подготовить следующий шаг",
                "deal": self.deal.pk,
                "client": self.company.pk,
                "due_at": "2026-03-20T10:00:00+06:00",
                "status": TaskStatus.IN_PROGRESS,
                "priority": "high",
                "task_type": task_type.pk,
                "communication_channel": channel.pk,
                "related_touch": touch.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], TaskStatus.IN_PROGRESS)
        self.assertEqual(response.data["status_label"], "В работе")
        self.assertEqual(response.data["priority"], "high")
        self.assertEqual(response.data["task_type"], task_type.pk)
        self.assertEqual(response.data["task_type_name"], "Квалификация")
        self.assertIsNone(response.data["task_type_category"])
        self.assertNotIn("task_type_category_name", response.data)
        self.assertIsNone(response.data["communication_channel"])
        self.assertNotIn("communication_channel_name", response.data)
        self.assertEqual(response.data["related_touch"], touch.pk)
        self.assertEqual(response.data["related_touch_subject"], "Первичный звонок")

    def test_task_type_meta_returns_category_driven_fields_without_group(self):
        later_task_type = TaskType.objects.create(
            name="Коммерческое предложение",
            group=TaskTypeGroup.CLIENT_TASK,
            sort_order=20,
        )
        earlier_task_type = TaskType.objects.create(
            name="Первичный контакт",
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=10,
        )

        response = self.client.get(reverse("meta-task-types"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], earlier_task_type.pk)
        self.assertEqual(response.data[0]["sort_order"], 10)
        self.assertEqual(response.data[1]["id"], later_task_type.pk)
        self.assertNotIn("group", response.data[1])
        self.assertNotIn("group_label", response.data[1])

    def test_task_category_and_task_type_meta_are_filtered_by_user_roles(self):
        developer_role = UserRole.objects.create(code="developer", name="Разработчик", sort_order=10)
        technical_category = TaskCategory.objects.create(
            code="technical_task",
            name="Техническая задача",
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=10,
        )
        technical_category.allowed_roles.add(developer_role)
        sales_category = TaskCategory.objects.create(
            code="sales_task",
            name="Задача продаж",
            group=TaskTypeGroup.CLIENT_TASK,
            sort_order=20,
        )
        TaskType.objects.create(
            name="Исправить баг",
            category=technical_category,
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=10,
        )
        TaskType.objects.create(
            name="Созвон с клиентом",
            category=sales_category,
            group=TaskTypeGroup.CLIENT_TASK,
            sort_order=20,
        )

        categories_response = self.client.get(reverse("meta-task-categories"))
        task_types_response = self.client.get(reverse("meta-task-types"))

        self.assertEqual(categories_response.status_code, status.HTTP_200_OK)
        self.assertEqual(task_types_response.status_code, status.HTTP_200_OK)
        category_names = {item["name"] for item in categories_response.data}
        task_type_names = {item["name"] for item in task_types_response.data}
        self.assertNotIn("Техническая задача", category_names)
        self.assertNotIn("Исправить баг", task_type_names)
        self.assertIn("Задача продаж", category_names)
        self.assertIn("Созвон с клиентом", task_type_names)

        UserRoleAssignment.objects.create(user=self.user, role=developer_role)

        categories_response = self.client.get(reverse("meta-task-categories"))
        task_types_response = self.client.get(reverse("meta-task-types"))

        category_names = {item["name"] for item in categories_response.data}
        task_type_names = {item["name"] for item in task_types_response.data}
        self.assertIn("Техническая задача", category_names)
        self.assertIn("Исправить баг", task_type_names)
        self.assertIn("Созвон с клиентом", task_type_names)

    def test_task_create_rejects_task_type_from_unavailable_role_category(self):
        developer_role = UserRole.objects.create(code="developer", name="Разработчик", sort_order=10)
        technical_category = TaskCategory.objects.create(
            code="technical_task",
            name="Техническая задача",
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=10,
        )
        technical_category.allowed_roles.add(developer_role)
        technical_task_type = TaskType.objects.create(
            name="Исправить баг",
            category=technical_category,
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=10,
        )

        response = self.client.post(
            reverse("activities-list"),
            {
                "type": "task",
                "subject": "Исправить баг",
                "task_type": technical_task_type.pk,
                "client": self.company.pk,
                "due_at": "2026-03-20T10:00:00+06:00",
                "status": TaskStatus.TODO,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["task_type"][0], "Этот тип задачи недоступен для ваших ролей.")

    def test_task_type_meta_returns_auto_touch_fields(self):
        task_type = TaskType.objects.create(
            name="Связаться повторно",
            group=TaskTypeGroup.CLIENT_TASK,
            auto_touch_on_done=True,
            touch_result="Связались повторно",
            sort_order=30,
        )

        response = self.client.get(reverse("meta-task-types"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matched = next(item for item in response.data if item["id"] == task_type.pk)
        self.assertTrue(matched["auto_touch_on_done"])
        self.assertEqual(matched["touch_result"], "Связались повторно")

    def test_task_type_meta_returns_auto_task_fields(self):
        auto_task_type = TaskType.objects.create(
            name="Подготовить договор",
            group=TaskTypeGroup.INTERNAL_TASK,
            sort_order=40,
        )
        task_type = TaskType.objects.create(
            name="Провести встречу",
            group=TaskTypeGroup.CLIENT_TASK,
            auto_task_on_done=True,
            auto_task_type=auto_task_type,
            sort_order=30,
        )

        response = self.client.get(reverse("meta-task-types"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matched = next(item for item in response.data if item["id"] == task_type.pk)
        self.assertTrue(matched["auto_task_on_done"])
        self.assertEqual(matched["auto_task_type"], auto_task_type.pk)
        self.assertEqual(matched["auto_task_type_name"], "Подготовить договор")

    def test_internal_task_with_auto_follow_up_creates_next_task_without_manual_follow_up(self):
        auto_task_type = TaskType.objects.create(
            name="Согласовать договор",
            group=TaskTypeGroup.INTERNAL_TASK,
        )
        task_type = TaskType.objects.create(
            name="Подготовить договор",
            group=TaskTypeGroup.INTERNAL_TASK,
            auto_task_on_done=True,
            auto_task_type=auto_task_type,
        )
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Подготовить договор",
            task_type=task_type,
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        response = self.client.patch(
            reverse("activities-detail", kwargs={"pk": task.pk}),
            {
                "is_done": True,
                "result": "Договор подготовлен",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        follow_up_task = Activity.objects.exclude(pk=task.pk).get(task_type=auto_task_type)
        self.assertEqual(follow_up_task.subject, "Согласовать договор")
        self.assertEqual(follow_up_task.status, TaskStatus.TODO)
        self.assertFalse(follow_up_task.is_done)
        self.assertEqual(follow_up_task.deal_id, self.deal.pk)
        self.assertEqual(follow_up_task.client_id, self.company.pk)

    def test_company_note_draft_writes_author_and_timestamp(self):
        response = self.client.patch(
            reverse("clients-detail", kwargs={"pk": self.company.pk}),
            {"note_draft": "Любят общаться в Telegram"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.company.refresh_from_db()
        self.assertRegex(self.company.notes, r"\d{2}\.\d{2}\.\d{4}")
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
        Activity.objects.create(
            type=ActivityType.TASK,
            subject="Активная задача по сделке",
            deal=self.deal,
            client=self.company,
            due_at=timezone.now() + timedelta(days=1),
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
        self.assertIn("Результат: Статус сделки изменён: Первичный контакт -> Переговоры", self.company.events)

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

    def test_task_can_be_created_without_subject_when_task_type_selected(self):
        task_type = TaskType.objects.create(name="Подготовить КП", group=TaskTypeGroup.INTERNAL_TASK)

        response = self.client.post(
            reverse("activities-list"),
            {
                "type": ActivityType.TASK,
                "subject": "",
                "task_type": task_type.pk,
                "client": self.company.pk,
                "deal": self.deal.pk,
                "due_at": "2026-03-20T10:00:00+06:00",
                "status": TaskStatus.TODO,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["subject"], "Подготовить КП")
