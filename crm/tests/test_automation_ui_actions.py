from django.test import SimpleTestCase

from crm.services.automation_ui_actions import get_available_actions_for_event


class AutomationUiActionsTests(SimpleTestCase):
    def test_call_completed_actions_match_expected_manager_shortcuts(self):
        action_ids = [item["id"] for item in get_available_actions_for_event("call_completed")]
        self.assertEqual(action_ids, ["schedule_meeting", "send_proposal", "create_task"])

    def test_meeting_completed_actions_match_expected_manager_shortcuts(self):
        action_ids = [item["id"] for item in get_available_actions_for_event("meeting_completed")]
        self.assertEqual(action_ids, ["send_proposal", "prepare_contract", "send_materials"])
