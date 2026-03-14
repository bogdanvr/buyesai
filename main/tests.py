import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Client, Contact, Lead, LeadSource
from main.models import FormSubmission


@override_settings(
    BOT_TOKEN="",
    TELEGRAM_CHAT_CHANNEL="",
    TELEGRAM_SUPER_GROUP="",
    TELEGRAM_CHAT_ID="",
    DADATA_KEY="",
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

    def test_falls_back_to_okved_when_industry_missing(self):
        response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Мария",
                        "phone": "+79993334455",
                        "company_data": {
                            "name": "ООО Тест",
                            "inn": "7707654321",
                            "okved": "46.90",
                        },
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        client = Client.objects.get(inn="7707654321")
        self.assertEqual(client.industry, "ОКВЭД 46.90")

    @override_settings(DADATA_KEY="test-token")
    @patch("main.views.Dadata")
    def test_enriches_company_and_creates_director_contact_from_dadata_find_by_id(self, dadata_cls):
        dadata_instance = dadata_cls.return_value
        dadata_instance.find_by_id.return_value = {
            "suggestions": [
                {
                    "value": 'ООО "ЭНЕРГОЭКСПЕРТ"',
                    "data": {
                        "inn": "5503190710",
                        "kpp": "550301001",
                        "ogrn": "1205500003763",
                        "okved": "25.99",
                        "okveds": [
                            {
                                "main": True,
                                "code": "25.99",
                                "name": "Производство прочих готовых металлических изделий",
                            },
                            {
                                "main": False,
                                "code": "46.90",
                                "name": "Торговля оптовая неспециализированная",
                            },
                        ],
                        "management": {
                            "name": "Верхоланцев Никита Валерьевич",
                            "post": "ДИРЕКТОР",
                        },
                        "phones": [
                            {"value": "+7 905 9405785"},
                        ],
                        "address": {
                            "value": "г Омск, ул 22 Партсъезда, д 51Г, офис 4",
                        },
                        "name": {
                            "full_with_opf": 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ЭНЕРГОЭКСПЕРТ"',
                            "short_with_opf": 'ООО "ЭНЕРГОЭКСПЕРТ"',
                        },
                    },
                }
            ]
        }

        response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Иван",
                        "phone": "+79990000000",
                        "company": "Энергоэксперт",
                        "company_inn": "5503190710",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        dadata_instance.find_by_id.assert_called_once_with("party", "5503190710")

        client = Client.objects.get(inn="5503190710")
        self.assertEqual(client.okved, "25.99")
        self.assertEqual(client.industry, "Производство прочих готовых металлических изделий")
        self.assertEqual(len(client.okveds), 2)
        self.assertEqual(client.okveds[1]["code"], "46.90")

        director = Contact.objects.get(client=client)
        self.assertEqual(director.first_name, "Верхоланцев")
        self.assertEqual(director.last_name, "Никита Валерьевич")
        self.assertEqual(director.position, "ДИРЕКТОР")
        self.assertEqual(director.phone, "+7 905 9405785")

    @override_settings(DADATA_KEY="test-token")
    @patch("main.views.Dadata")
    def test_dadata_party_by_inn_endpoint_returns_profile(self, dadata_cls):
        dadata_instance = dadata_cls.return_value
        dadata_instance.find_by_id.return_value = {
            "suggestions": [
                {
                    "value": 'ООО "ЭНЕРГОЭКСПЕРТ"',
                    "data": {
                        "inn": "5503190710",
                        "okved": "25.99",
                        "okveds": [
                            {
                                "main": True,
                                "code": "25.99",
                                "name": "Производство прочих готовых металлических изделий",
                            },
                            {
                                "main": False,
                                "code": "46.90",
                                "name": "Торговля оптовая неспециализированная",
                            },
                        ],
                        "name": {
                            "short_with_opf": 'ООО "ЭНЕРГОЭКСПЕРТ"',
                        },
                    },
                }
            ]
        }

        response = self.client.get(reverse("dadata_party_by_inn"), {"inn": "5503190710"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["profile"]["okved"], "25.99")
        self.assertEqual(
            payload["profile"]["industry"],
            "Производство прочих готовых металлических изделий",
        )
        self.assertEqual(len(payload["profile"]["okveds"]), 2)
