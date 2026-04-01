from django.test import TestCase

from api.v1.leads.serializers import LeadSerializer
from crm.services.lead_services import create_lead_from_payload
from main.models import WebsiteSession, WebsiteSessionEvent


class LeadSerializerTrackingTests(TestCase):
    def test_serializer_keeps_site_actions_for_ui_block(self):
        session = WebsiteSession.objects.create(
            session_id="serializer-tracking-session",
            utm_source="google",
            utm_campaign="campaign-1",
            utm_content="creative-7",
        )
        WebsiteSessionEvent.objects.create(
            session=session,
            event_type="page_view",
            payload={},
        )
        WebsiteSessionEvent.objects.create(
            session=session,
            event_type="form_submitted",
            payload={"form_type": "hero"},
        )

        lead = create_lead_from_payload(
            form_type="hero",
            payload={
                "name": "Иван",
                "phone": "+79990000000",
                "utm_data": {"utm_source": "google"},
            },
            website_session=session,
        )

        data = LeadSerializer(instance=lead).data

        self.assertEqual(data["website_session_id"], "serializer-tracking-session")
        self.assertCountEqual(
            data["source_names"],
            [
                "Просмотр страницы",
                "Клик по форме hero",
            ],
        )
        self.assertEqual(data.get("source_name", ""), "")
        self.assertNotIn("Источник трафика: google", data["source_names"])
