from django.test import SimpleTestCase

from crm.models.touch import normalize_touch_channel_code, resolve_touch_event_type


class TouchEventTypeResolutionTests(SimpleTestCase):
    def test_normalizes_proposal_and_documents_channel_aliases(self):
        self.assertEqual(normalize_touch_channel_code("КП"), "proposal")
        self.assertEqual(normalize_touch_channel_code("Коммерческое предложение"), "proposal")
        self.assertEqual(normalize_touch_channel_code("Документы"), "documents")

    def test_falls_back_to_transport_event_for_plain_email(self):
        self.assertEqual(
            resolve_touch_event_type(channel_code="Email", direction="outgoing", result_code=""),
            "email_sent",
        )

    def test_uses_message_event_names_for_messengers(self):
        self.assertEqual(
            resolve_touch_event_type(channel_code="Telegram", direction="outgoing", result_code=""),
            "telegram_message_sent",
        )
        self.assertEqual(
            resolve_touch_event_type(channel_code="WhatsApp", direction="incoming", result_code=""),
            "whatsapp_message_received",
        )

    def test_maps_call_no_answer(self):
        self.assertEqual(
            resolve_touch_event_type(channel_code="Телефон", direction="outgoing", result_code="no_answer"),
            "call_no_answer",
        )

    def test_falls_back_to_completed_call_and_meeting(self):
        self.assertEqual(
            resolve_touch_event_type(channel_code="Телефон", direction="outgoing", result_code=""),
            "call_completed",
        )
        self.assertEqual(
            resolve_touch_event_type(channel_code="Встреча", direction="outgoing", result_code=""),
            "meeting_completed",
        )

    def test_maps_business_result_codes_to_catalog_event_types(self):
        self.assertEqual(
            resolve_touch_event_type(channel_code="КП", direction="outgoing", result_code="proposal_received"),
            "proposal_received_by_client",
        )
        self.assertEqual(
            resolve_touch_event_type(channel_code="Документы", direction="outgoing", result_code="contract_agreed"),
            "contract_agreed",
        )
        self.assertEqual(
            resolve_touch_event_type(channel_code="Телефон", direction="outgoing", result_code="meeting_scheduled"),
            "meeting_scheduled",
        )
        self.assertEqual(
            resolve_touch_event_type(channel_code="Email", direction="outgoing", result_code="payment_confirmed"),
            "payment_confirmed",
        )
