from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from datetime import timedelta

from crm.models import Activity, AutomationRule, Client, ClientDocument, CommunicationChannel, Contact, Deal, DealDocument, DealStage, Lead, LeadStatus, NextStepTemplate, Touch, TouchResult
from crm.models.activity import ActivityType, TaskStatus


class TouchesApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_touch",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.channel = CommunicationChannel.objects.create(name="Телефон Touch API")
        self.lead_status = LeadStatus.objects.create(
            name="В работе Touch API",
            code="touch_api_in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.touch_result = TouchResult.objects.create(
            name="Назначен следующий шаг Touch API",
            code="touch_api_follow_up_result",
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
            name="В работе Сделка Touch API",
            code="touch_api_deal_in_progress",
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
            client=self.company,
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
        self.assertEqual(response.data["channel_name"], self.channel.name)
        self.assertEqual(response.data["result_option_name"], self.touch_result.name)
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
        result_payload = next(item for item in response.data if item["id"] == self.touch_result.pk)
        self.assertEqual(result_payload["code"], self.touch_result.code)
        self.assertEqual(result_payload["group"], "follow_up")
        self.assertEqual(result_payload["class"], "neutral")
        self.assertEqual(result_payload["requires_next_step"], True)
        self.assertEqual(result_payload["allowed_touch_types"], ["call"])
        self.assertNotIn("lead_status_ids", result_payload)
        self.assertNotIn("deal_stage_ids", result_payload)

    def test_communication_channel_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-communication-channels"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        channel_payload = next(item for item in response.data if item["id"] == self.channel.pk)
        self.assertEqual(channel_payload["touch_result_ids"], [self.touch_result.pk])

    def test_lead_status_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-lead-statuses"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead_status_payload = next(item for item in response.data if item["id"] == self.lead_status.pk)
        self.assertEqual(lead_status_payload["touch_result_ids"], [self.touch_result.pk])

    def test_deal_stage_meta_returns_touch_results(self):
        response = self.client.get(reverse("meta-deal-stages"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stage_payload = next(item for item in response.data if item["id"] == self.stage.pk)
        self.assertEqual(stage_payload["touch_result_ids"], [self.touch_result.pk])

    def test_unsupported_channel_does_not_block_manual_save(self):
        email_channel = CommunicationChannel.objects.create(name="Email")

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": "2026-03-18T10:00:00+06:00",
                "channel": email_channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Письмо отправлено",
                "next_step_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["result_option_name"], self.touch_result.name)

    def test_touch_with_auto_follow_up_rule_saves_without_next_step_and_creates_task(self):
        waiting_payment_result = TouchResult.objects.create(
            name="Ждём оплату",
            code="waiting_payment",
            group="payment",
            result_class="neutral",
            requires_next_step=False,
            allowed_touch_types=["call"],
            sort_order=30,
        )
        self.channel.touch_results.add(waiting_payment_result)
        self.stage.touch_results.add(waiting_payment_result)
        next_step_template = NextStepTemplate.objects.create(
            code="payment_control_next_day",
            name="Контроль оплаты на следующий день",
        )
        AutomationRule.objects.create(
            event_type="payment_waiting",
            ui_mode="next_step_prompt",
            ui_priority="medium",
            write_timeline=True,
            show_in_summary=False,
            show_in_attention_queue=False,
            merge_key="invoice",
            auto_open_panel=False,
            create_message=False,
            create_touchpoint_mode="none",
            allow_auto_create_task=True,
            require_manager_confirmation=False,
            next_step_template=next_step_template,
            is_active=True,
            sort_order=10,
        )

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": timezone.now().isoformat(),
                "channel": self.channel.pk,
                "result_option": waiting_payment_result.pk,
                "direction": "outgoing",
                "summary": "Ожидаем оплату счета",
                "owner": self.user.pk,
                "deal": self.deal.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        follow_up_task = Activity.objects.filter(
            type=ActivityType.TASK,
            deal=self.deal,
            subject="Контроль оплаты на следующий день",
        ).order_by("-id").first()
        self.assertIsNotNone(follow_up_task)
        self.assertEqual(follow_up_task.status, TaskStatus.TODO)
        self.assertEqual(follow_up_task.communication_channel_id, self.channel.pk)

    def test_can_close_selected_related_task_from_touch(self):
        task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Проконтролировать оплату",
            due_at=timezone.now() + timedelta(days=1),
            status=TaskStatus.TODO,
            client=self.company,
            deal=self.deal,
            created_by=self.user,
        )

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": timezone.now().isoformat(),
                "channel": self.channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Клиент обещал оплатить сегодня",
                "next_step_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "owner": self.user.pk,
                "client": self.company.pk,
                "deal": self.deal.pk,
                "task": task.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.DONE)
        self.assertEqual(task.result, "Клиент обещал оплатить сегодня")
        self.assertEqual(response.data["task_subject"], "Проконтролировать оплату")

    def test_editing_existing_touch_does_not_reinitialize_auto_follow_up_task(self):
        waiting_payment_result = TouchResult.objects.create(
            name="Ждём оплату для редактирования",
            code="waiting_payment",
            group="payment",
            result_class="neutral",
            requires_next_step=False,
            allowed_touch_types=["call"],
            sort_order=31,
        )
        self.channel.touch_results.add(waiting_payment_result)
        self.stage.touch_results.add(waiting_payment_result)
        next_step_template = NextStepTemplate.objects.create(
            code="payment_control_next_day_edit_once",
            name="Контроль оплаты на следующий день",
        )
        AutomationRule.objects.create(
            event_type="payment_waiting",
            ui_mode="next_step_prompt",
            ui_priority="medium",
            write_timeline=True,
            show_in_summary=False,
            show_in_attention_queue=False,
            merge_key="invoice",
            auto_open_panel=False,
            create_message=False,
            create_touchpoint_mode="none",
            allow_auto_create_task=True,
            require_manager_confirmation=False,
            next_step_template=next_step_template,
            is_active=True,
            sort_order=10,
        )

        create_response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": timezone.now().isoformat(),
                "channel": self.channel.pk,
                "result_option": waiting_payment_result.pk,
                "direction": "outgoing",
                "summary": "Первичное ожидание оплаты",
                "owner": self.user.pk,
                "deal": self.deal.pk,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        touch_id = create_response.data["id"]
        original_task = Activity.objects.filter(
            type=ActivityType.TASK,
            deal=self.deal,
            subject="Контроль оплаты на следующий день",
        ).order_by("-id").first()
        self.assertIsNotNone(original_task)
        original_task.status = TaskStatus.DONE
        original_task.is_done = True
        original_task.completed_at = timezone.now()
        original_task.save(update_fields=["status", "is_done", "completed_at", "updated_at"])

        update_response = self.client.patch(
            reverse("touches-detail", kwargs={"pk": touch_id}),
            {
                "summary": "Отредактированное касание без новой задачи",
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        tasks = Activity.objects.filter(
            type=ActivityType.TASK,
            deal=self.deal,
            subject="Контроль оплаты на следующий день",
        ).order_by("id")
        self.assertEqual(tasks.count(), 1)
        original_task.refresh_from_db()
        self.assertEqual(original_task.status, TaskStatus.DONE)

    def test_cannot_select_task_from_another_company(self):
        other_company = Client.objects.create(name="Other company")
        other_task = Activity.objects.create(
            type=ActivityType.TASK,
            subject="Чужая задача",
            due_at=timezone.now() + timedelta(days=1),
            status=TaskStatus.TODO,
            client=other_company,
            created_by=self.user,
        )

        response = self.client.post(
            reverse("touches-list"),
            {
                "happened_at": timezone.now().isoformat(),
                "channel": self.channel.pk,
                "result_option": self.touch_result.pk,
                "direction": "outgoing",
                "summary": "Попытка закрыть чужую задачу",
                "next_step_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "owner": self.user.pk,
                "client": self.company.pk,
                "task": other_task.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task", response.data)

    def test_channel_touch_results_do_not_block_manual_save(self):
        restricted_channel = CommunicationChannel.objects.create(name="Telegram")
        allowed_channel_result = TouchResult.objects.create(
            name="Только для фильтра канала",
            code="touch_api_channel_filter_only",
            group="follow_up",
            result_class="neutral",
            requires_next_step=False,
            allowed_touch_types=[],
            sort_order=20,
        )
        manual_result = TouchResult.objects.create(
            name="Ручной результат вне канала",
            code="touch_api_manual_outside_channel",
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
