from django.core.management import call_command
from django.test import TestCase

from crm.models import AutomationRule, TouchResult


class AutomationFixtureMatrixTests(TestCase):
    def test_split_fixtures_load_successfully(self):
        call_command(
            "loaddata",
            "touch_results",
            "outcome_catalog",
            "next_step_templates",
            "automation_rules",
            verbosity=0,
        )

        self.assertEqual(TouchResult.objects.count(), 37)
        self.assertEqual(AutomationRule.objects.count(), 49)
        self.assertTrue(AutomationRule.objects.filter(event_type="telegram_message_sent").exists())
        self.assertTrue(AutomationRule.objects.filter(event_type="whatsapp_message_received").exists())
        self.assertTrue(AutomationRule.objects.filter(event_type="call_completed").exists())
        self.assertTrue(AutomationRule.objects.filter(event_type="meeting_completed").exists())
        self.assertFalse(AutomationRule.objects.filter(event_type="telegram_sent").exists())
        self.assertFalse(AutomationRule.objects.filter(event_type="meeting_held").exists())

    def test_seed_fixture_rules_are_consistent_with_touch_results(self):
        call_command("loaddata", "automation_seed", verbosity=0)

        unresolved_event_types = []
        for rule in AutomationRule.objects.select_related("default_outcome", "next_step_template").all():
            if rule.default_outcome_id and not (
                TouchResult.objects.filter(code=rule.default_outcome.code).exists()
                or TouchResult.objects.filter(name=rule.default_outcome.name).exists()
            ):
                unresolved_event_types.append(rule.event_type)

        self.assertEqual(unresolved_event_types, [])
        self.assertEqual(
            set(
                AutomationRule.objects.filter(allow_auto_create_task=True).values_list("event_type", flat=True)
            ),
            {"meeting_scheduled", "meeting_rescheduled"},
        )
        self.assertEqual(
            set(
                AutomationRule.objects.filter(create_message=True).values_list("event_type", flat=True)
            ),
            {
                "email_sent",
                "email_received",
                "telegram_message_sent",
                "telegram_message_received",
                "whatsapp_message_sent",
                "whatsapp_message_received",
            },
        )
