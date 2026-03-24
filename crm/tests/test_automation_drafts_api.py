from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Activity, AutomationDraft, AutomationQueueItem, AutomationRule, Client, CommunicationChannel, Deal, DealStage, NextStepTemplate, OutcomeCatalog, Touch, TouchResult


class AutomationDraftsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_automation",
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
        self.deal = Deal.objects.create(title="Сделка для automation drafts", stage=self.stage, client=self.company)
        self.channel = CommunicationChannel.objects.create(name="Email")
        self.touch_result = TouchResult.objects.create(
            code="waiting_feedback",
            name="Ждём обратную связь",
            group="waiting",
            result_class="neutral",
        )
        self.outcome = OutcomeCatalog.objects.create(code="waiting_feedback", name="Ждём обратную связь")
        self.template = NextStepTemplate.objects.create(code="followup_after_2_days", name="Фоллоу-ап через 2 дня")
        self.rule = AutomationRule.objects.create(
            event_type="email_sent",
            ui_mode="draft_touch",
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

    def test_creating_touch_creates_pending_automation_drafts(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            next_step_at=timezone.now() + timedelta(days=2),
            owner=self.user,
            deal=self.deal,
        )

        drafts = AutomationDraft.objects.filter(source_touch=touch, status="pending").order_by("draft_kind")
        self.assertEqual(drafts.count(), 2)
        self.assertEqual(set(drafts.values_list("draft_kind", flat=True)), {"touch", "next_step"})

        touch_draft = drafts.get(draft_kind="touch")
        self.assertEqual(touch_draft.source_event_type, "email_sent")
        self.assertEqual(touch_draft.touch_result, self.touch_result)
        self.assertEqual(touch_draft.proposed_next_step, "Фоллоу-ап через 2 дня")

    def test_confirm_touch_draft_applies_proposed_values_to_source_touch(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            owner=self.user,
            deal=self.deal,
        )
        draft = AutomationDraft.objects.get(source_touch=touch, draft_kind="touch", status="pending")

        response = self.client.post(
            reverse("automation-drafts-confirm", kwargs={"pk": draft.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        draft.refresh_from_db()
        touch.refresh_from_db()
        self.assertEqual(draft.status, "confirmed")
        self.assertEqual(touch.result_option, self.touch_result)
        self.assertEqual(touch.next_step, "Фоллоу-ап через 2 дня")

    def test_touch_rule_with_create_mode_creates_automation_touch(self):
        self.rule.create_touchpoint_mode = "create"
        self.rule.next_step_template = None
        self.rule.require_manager_confirmation = False
        self.rule.show_in_attention_queue = False
        self.rule.save()

        source_touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            owner=self.user,
            deal=self.deal,
        )

        touches = list(Touch.objects.filter(deal=self.deal).order_by("id"))
        self.assertEqual(len(touches), 2)
        self.assertEqual(touches[0].pk, source_touch.pk)

        created_touch = touches[1]
        self.assertEqual(created_touch.result_option, self.touch_result)
        self.assertEqual(created_touch.channel, self.channel)
        self.assertEqual(created_touch.direction, "outgoing")
        self.assertEqual(created_touch.summary, "Отправили письмо")
        self.assertEqual(created_touch.owner, self.user)
        self.assertEqual(created_touch.deal_id, self.deal.pk)
        self.assertEqual(created_touch.client_id, self.company.pk)
        self.assertFalse(AutomationDraft.objects.filter(source_touch=source_touch, draft_kind="touch").exists())
        self.assertEqual(Touch.objects.filter(deal=self.deal).count(), 2)

    def test_can_list_pending_automation_drafts(self):
        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо",
            owner=self.user,
            deal=self.deal,
        )

        response = self.client.get(reverse("automation-drafts-list"), {"status": "pending", "deal": self.deal.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["source_touch"], touch.pk)

    def test_business_touch_result_matches_catalog_event_type(self):
        proposal_channel = CommunicationChannel.objects.create(name="КП")
        proposal_result = TouchResult.objects.create(
            code="proposal_received",
            name="КП получено клиентом",
            group="waiting",
            result_class="neutral",
        )
        proposal_rule = AutomationRule.objects.create(
            event_type="proposal_received_by_client",
            ui_mode="draft_touch",
            ui_priority="high",
            show_in_summary=True,
            show_in_attention_queue=True,
            merge_key="proposal",
            create_touchpoint_mode="draft",
            default_outcome=self.outcome,
            require_manager_confirmation=True,
            next_step_template=self.template,
            is_active=True,
            sort_order=20,
        )

        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=proposal_channel,
            result_option=proposal_result,
            direction="outgoing",
            summary="КП отправлено и клиент подтвердил получение",
            owner=self.user,
            deal=self.deal,
        )

        draft = AutomationDraft.objects.filter(
            source_touch=touch,
            automation_rule=proposal_rule,
            status="pending",
        ).first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.source_event_type, "proposal_received_by_client")

    def test_touch_rule_with_write_timeline_false_skips_touch_events(self):
        silent_company = Client.objects.create(name="Silent Co")
        silent_deal = Deal.objects.create(title="Silent deal", stage=self.stage, client=silent_company)
        silent_company.events = ""
        silent_company.save(update_fields=["events"])
        silent_deal.events = ""
        silent_deal.save(update_fields=["events"])

        silent_rule = AutomationRule.objects.create(
            event_type="telegram_message_sent",
            ui_mode="history_only",
            ui_priority="low",
            write_timeline=False,
            create_touchpoint_mode="none",
            is_active=True,
            sort_order=30,
        )
        telegram_channel = CommunicationChannel.objects.create(name="Telegram")

        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=telegram_channel,
            direction="outgoing",
            summary="Отправили сообщение",
            owner=self.user,
            deal=silent_deal,
            client=silent_company,
        )

        silent_deal.refresh_from_db()
        silent_company.refresh_from_db()
        self.assertEqual(silent_deal.events, "")
        self.assertEqual(silent_company.events, "")
        self.assertEqual(silent_rule.event_type, "telegram_message_sent")
        self.assertTrue(AutomationDraft.objects.filter(source_touch=touch).count() == 0)

    def test_touch_rule_with_auto_create_task_creates_follow_up_task(self):
        auto_rule = self.rule
        auto_rule.ui_mode = "next_step_prompt"
        auto_rule.ui_priority = "medium"
        auto_rule.show_in_summary = True
        auto_rule.create_touchpoint_mode = "none"
        auto_rule.allow_auto_create_task = True
        auto_rule.require_manager_confirmation = False
        auto_rule.next_step_template = self.template
        auto_rule.save()

        touch = Touch.objects.create(
            happened_at=timezone.now(),
            channel=self.channel,
            direction="outgoing",
            summary="Отправили письмо с предложением",
            next_step_at=timezone.now() + timedelta(days=2),
            owner=self.user,
            deal=self.deal,
        )

        task = Activity.objects.filter(subject="Фоллоу-ап через 2 дня", deal=self.deal, client=self.company).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.subject, "Фоллоу-ап через 2 дня")
        self.assertEqual(task.deal_id, self.deal.pk)
        self.assertEqual(task.client_id, self.company.pk)
        self.assertEqual(task.communication_channel_id, self.channel.pk)
        self.assertFalse(
            AutomationQueueItem.objects.filter(
                source_touch=touch,
                item_kind="next_step",
                status="pending",
            ).exists()
        )
        self.assertEqual(auto_rule.event_type, "email_sent")
