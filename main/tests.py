import json

from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Client, Lead, LeadSource
from main.models import FormSubmission


@override_settings(
    BOT_TOKEN="",
    TELEGRAM_CHAT_CHANNEL="",
    TELEGRAM_SUPER_GROUP="",
    TELEGRAM_CHAT_ID="",
)
class SendFormViewTests(TestCase):
    def test_creates_form_submission_and_crm_lead(self):
        response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Иван",
                        "phone": "+79990000000",
                        "company": "Acme",
                        "company_data": {
                            "name": "ООО «Акме»",
                            "inn": "7701234567",
                            "address": "г. Москва, ул. Тестовая, д. 1",
                            "industry": "Разработка ПО",
                            "okved": "62.01",
                        },
                        "message": "Нужна автоматизация",
                        "utm_data": {"utm_source": "google"},
                    },
                }
            ),
            content_type="application/json",
            HTTP_REFERER="https://example.com/?utm_campaign=spring",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertEqual(Lead.objects.count(), 1)

        form_submission = FormSubmission.objects.get()
        lead = Lead.objects.get()
        source = LeadSource.objects.get()
        client = Client.objects.get()

        self.assertEqual(form_submission.form_type, "hero")
        self.assertEqual(lead.name, "Иван")
        self.assertEqual(lead.phone, "+79990000000")
        self.assertEqual(lead.company, "ООО «Акме»")
        self.assertEqual(lead.source_id, source.id)
        self.assertEqual(lead.client_id, client.id)
        self.assertEqual(source.code, "site-hero")
        self.assertEqual(lead.payload.get("form_submission_id"), form_submission.id)
        self.assertEqual(lead.utm_data.get("utm_source"), "google")
        self.assertEqual(response.json().get("crm_lead_id"), lead.id)
        self.assertEqual(client.name, "ООО «Акме»")
        self.assertEqual(client.inn, "7701234567")
        self.assertEqual(client.address, "г. Москва, ул. Тестовая, д. 1")
        self.assertEqual(client.industry, "Разработка ПО")
        self.assertEqual(client.okved, "62.01")

    def test_reuses_existing_company_for_form_lead(self):
        existing = Client.objects.create(name="Acme")

        first_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "quiz",
                    "payload": {
                        "name": "Петр",
                        "phone": "+79991111111",
                        "company": "ACME",
                    },
                }
            ),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "plan",
                    "payload": {
                        "name": "Сергей",
                        "phone": "+79992222222",
                        "company": "acme",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Client.objects.filter(name__iexact="acme").count(), 1)
        self.assertEqual(Lead.objects.count(), 2)
        self.assertEqual(Lead.objects.filter(client=existing).count(), 2)
