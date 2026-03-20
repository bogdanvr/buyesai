from django.core.management import call_command
from django.test import TestCase

from crm.models import AutomationRule, NextStepTemplate, OutcomeCatalog, TouchResult


class AutomationSeedFixtureTests(TestCase):
    def test_full_automation_seed_fixture_loads_successfully(self):
        call_command("loaddata", "automation_seed", verbosity=0)

        self.assertEqual(TouchResult.objects.count(), 36)
        self.assertEqual(OutcomeCatalog.objects.count(), 17)
        self.assertEqual(NextStepTemplate.objects.count(), 16)
        self.assertEqual(AutomationRule.objects.count(), 49)

        self.assertEqual(
            TouchResult.objects.get(code="rejected_competitor").name,
            "Отказ — выбрали конкурента",
        )
        self.assertTrue(TouchResult.objects.get(code="rejected_competitor").requires_loss_reason)
        self.assertEqual(
            OutcomeCatalog.objects.get(code="invoice_accepted").name,
            "Счёт принят",
        )
        self.assertEqual(
            NextStepTemplate.objects.get(code="revise_contract").name,
            "Доработать договор",
        )

        telegram_rule = AutomationRule.objects.get(event_type="telegram_message_sent")
        self.assertEqual(telegram_rule.create_touchpoint_mode, "draft")
        self.assertEqual(telegram_rule.default_outcome.code, "waiting_feedback")
        self.assertEqual(telegram_rule.next_step_template.code, "followup_after_1_day")
        self.assertEqual(telegram_rule.merge_key, "telegram")

        meeting_rule = AutomationRule.objects.get(event_type="meeting_scheduled")
        self.assertEqual(meeting_rule.ui_mode, "next_step_prompt")
        self.assertTrue(meeting_rule.allow_auto_create_task)
