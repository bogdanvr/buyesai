from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Activity, AutomationQueueItem, AutomationRule, Client, CommunicationChannel, Deal, DealStage, NextStepTemplate, OutcomeCatalog, TaskType, Touch, TouchResult
from crm.models.activity import TaskTypeGroup


class AutomationQueueApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_automation_queue",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="Acme")
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(title="Сделка для automation queue", stage=self.stage, client=self.company)
        self.channel = CommunicationChannel.objects.create(name="Email")
        self.touch_result = TouchResult.objects.create(
            code="waiting_feedback",
            name="Ждём обратную связь",
            group="waiting",
            result_class="neutral",
        )
        self.client_task_type = TaskType.objects.create(
            name="Фоллоу-ап клиенту",
            group=TaskTypeGroup.CLIENT_TASK,
            is_active=True,
        )
        self.outcome = OutcomeCatalog.objects.create(code="waiting_feedback", name="Ждём обратную связь")
        self.template = NextStepTemplate.objects.create(code="followup_after_2_days", name="Фоллоу-ап через 2 дня")
        self.rule = AutomationRule.objects.create(
            event_type="email_sent",
            ui_mode="needs_attention",
            ui_priority="high",
            show_in_summary=True,
            show_in_attention_queue=True,
            merge_key="email",
            create_touchpoint_mode="draft",
            default_outcome=self.outcome,
            require_manager_confirmation=True,
            next_step_template=self.template,
            is_active=True,
            sort_order=10,
        )

    def test_creating_touch_creates_pending_queue_items(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            next_step_at=timezone.now() + timedelta(days=2),
            owner=self.user,
            deal=self.deal,
        )

        queue_items = AutomationQueueItem.objects.filter(source_touch=touch, status="pending").order_by("item_kind")
        self.assertEqual(queue_items.count(), 2)
        self.assertEqual(set(queue_items.values_list("item_kind", flat=True)), {"attention", "next_step"})

        next_step_item = queue_items.get(item_kind="next_step")
        self.assertEqual(next_step_item.source_event_type, "email_sent")
        self.assertEqual(next_step_item.proposed_next_step, "Фоллоу-ап через 2 дня")

    def test_confirm_next_step_queue_item_creates_task(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            next_step_at=timezone.now() + timedelta(days=2),
            owner=self.user,
            deal=self.deal,
        )
        queue_item = AutomationQueueItem.objects.get(source_touch=touch, item_kind="next_step", status="pending")

        response = self.client.post(
            reverse("automation-queue-confirm", kwargs={"pk": queue_item.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queue_item.refresh_from_db()
        self.assertEqual(queue_item.status, "resolved")
        self.assertIsNotNone(queue_item.created_task_id)
        created_task = Activity.objects.get(pk=queue_item.created_task_id)
        self.assertEqual(created_task.subject, "Фоллоу-ап через 2 дня")
        self.assertEqual(created_task.deal_id, self.deal.pk)
        self.assertEqual(created_task.task_type_id, self.client_task_type.pk)
        self.assertEqual(created_task.communication_channel_id, self.channel.pk)

    def test_can_list_pending_automation_queue_items(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            owner=self.user,
            deal=self.deal,
        )

        response = self.client.get(reverse("automation-queue-list"), {"status": "pending", "deal": self.deal.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["source_touch"], touch.pk)

    def test_queue_item_serializer_returns_available_actions_for_attention_event(self):
        incoming_rule = AutomationRule.objects.create(
            event_type="email_received",
            ui_mode="needs_attention",
            ui_priority="high",
            show_in_attention_queue=True,
            is_active=True,
            sort_order=20,
        )
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="incoming",
            summary="Клиент ответил на письмо",
            owner=self.user,
            deal=self.deal,
        )

        response = self.client.get(reverse("automation-queue-list"), {"status": "pending", "deal": self.deal.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        attention_item = next(item for item in payload if item["source_touch"] == touch.pk and item["item_kind"] == "attention")
        action_ids = [item["id"] for item in attention_item["available_actions"]]
        self.assertIn("reply", action_ids)
        self.assertIn("call", action_ids)
        self.assertIn("schedule_meeting", action_ids)
        self.assertIn("create_task", action_ids)
        self.assertEqual(incoming_rule.event_type, "email_received")

    def test_touch_result_change_dismisses_stale_pending_queue_items(self):
        incoming_rule = AutomationRule.objects.create(
            event_type="email_received",
            ui_mode="needs_attention",
            ui_priority="high",
            show_in_attention_queue=True,
            is_active=True,
            sort_order=20,
        )
        payment_outcome = OutcomeCatalog.objects.create(code="payment_confirmed", name="Оплата подтверждена")
        payment_result = TouchResult.objects.create(
            code="payment_confirmed",
            name="Оплата подтверждена",
            group="won_signal",
            result_class="won_signal",
        )
        payment_rule = AutomationRule.objects.create(
            event_type="payment_confirmed",
            ui_mode="needs_attention",
            ui_priority="critical",
            show_in_attention_queue=True,
            default_outcome=payment_outcome,
            next_step_template=self.template,
            is_active=True,
            sort_order=30,
        )

        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="incoming",
            summary="Клиент подтвердил оплату",
            owner=self.user,
            deal=self.deal,
        )

        stale_item = AutomationQueueItem.objects.get(
            source_touch=touch,
            automation_rule=incoming_rule,
            item_kind="attention",
        )
        self.assertEqual(stale_item.status, "pending")

        touch.result_option = payment_result
        touch.next_step_at = timezone.now() + timedelta(days=1)
        touch.save(update_fields=["result_option", "next_step_at", "updated_at"])

        stale_item.refresh_from_db()
        self.assertEqual(stale_item.status, "dismissed")

        current_items = AutomationQueueItem.objects.filter(
            source_touch=touch,
            automation_rule=payment_rule,
            status="pending",
        )
        self.assertEqual(current_items.count(), 2)
        self.assertEqual(set(current_items.values_list("item_kind", flat=True)), {"attention", "next_step"})
        self.assertEqual(
            current_items.get(item_kind="attention").title,
            "Оплата подтверждена",
        )
        self.assertEqual(
            current_items.get(item_kind="next_step").title,
            "Фоллоу-ап через 2 дня",
        )
