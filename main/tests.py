import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Client, Contact, Lead, LeadSource, TrafficSource
from main.models import FormSubmission, WebsiteSession, WebsiteSessionEvent


@override_settings(
    BOT_TOKEN="",
    TELEGRAM_CHAT_CHANNEL="",
    TELEGRAM_SUPER_GROUP="",
    TELEGRAM_CHAT_ID="",
    DADATA_KEY="",
)
class SendFormViewTests(TestCase):
    def test_tracks_website_session_and_first_message(self):
        response = self.client.post(
            reverse("track_website_session"),
            data=json.dumps(
                {
                    "session_id": "session-123",
                    "utm_source": "google",
                    "utm_medium": "cpc",
                    "utm_campaign": "spring_sale",
                    "utm_content": "ad-1",
                    "utm_term": "ai crm",
                    "yclid": "yclid-test",
                    "referer": "https://google.com/",
                    "landing_url": "https://buyes.pro/?utm_source=google",
                    "client_id": "12345.67890",
                    "page_url": "https://buyes.pro/?utm_source=google",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        session = WebsiteSession.objects.get(session_id="session-123")
        self.assertEqual(session.utm_source, "google")
        self.assertEqual(session.utm_campaign, "spring_sale")
        self.assertEqual(session.yclid, "yclid-test")
        self.assertEqual(session.client_id, "12345.67890")
        self.assertTrue(
            WebsiteSessionEvent.objects.filter(session=session, event_type="page_view").exists()
        )

        first_message_response = self.client.post(
            reverse("track_website_event"),
            data=json.dumps(
                {
                    "session_id": "session-123",
                    "event_type": "first_message_sent",
                    "message": "Подскажите по AI-аудиту",
                    "page_url": "https://buyes.pro/",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first_message_response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.first_message, "Подскажите по AI-аудиту")
        self.assertIsNotNone(session.first_message_at)

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
        client = Client.objects.get()

        self.assertEqual(form_submission.form_type, "hero")
        self.assertEqual(lead.name, "Иван")
        self.assertEqual(lead.phone, "+79990000000")
        self.assertEqual(lead.company, "ООО «Акме»")
        self.assertIsNone(lead.source_id)
        self.assertEqual(lead.client_id, client.id)
        self.assertEqual(TrafficSource.objects.count(), 0)
        self.assertEqual(lead.payload.get("form_submission_id"), form_submission.id)
        self.assertEqual(lead.utm_data.get("utm_source"), "google")
        self.assertEqual(response.json().get("crm_lead_id"), lead.id)
        self.assertEqual(client.name, "ООО «Акме»")
        self.assertEqual(client.inn, "7701234567")
        self.assertEqual(client.address, "г. Москва, ул. Тестовая, д. 1")
        self.assertEqual(client.industry, "Разработка ПО")
        self.assertEqual(client.okved, "62.01")

    def test_send_form_links_tracking_session_history_and_sources(self):
        self.client.post(
            reverse("track_website_session"),
            data=json.dumps(
                {
                    "session_id": "session-with-lead",
                    "utm_source": "google",
                    "utm_campaign": "campaign-1",
                    "utm_content": "creative-7",
                    "landing_url": "https://buyes.pro/?utm_source=google",
                    "page_url": "https://buyes.pro/?utm_source=google",
                }
            ),
            content_type="application/json",
        )
        self.client.post(
            reverse("track_website_event"),
            data=json.dumps(
                {
                    "session_id": "session-with-lead",
                    "event_type": "first_message_sent",
                    "message": "Нужен аудит процессов",
                    "page_url": "https://buyes.pro/",
                }
            ),
            content_type="application/json",
        )

        response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "session_id": "session-with-lead",
                        "name": "Иван",
                        "phone": "+79990000000",
                        "company": "Acme",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get()
        session = WebsiteSession.objects.get(session_id="session-with-lead")

        self.assertEqual(lead.website_session_id, session.id)
        self.assertIsNone(lead.source_id)
        self.assertEqual(
            [item["event"] for item in lead.history],
            ["page_view", "first_message_sent", "form_submitted"],
        )
        self.assertEqual(lead.history[-1]["form_type"], "hero")
        self.assertTrue(lead.sources.filter(name="Просмотр страницы").exists())
        self.assertTrue(lead.sources.filter(name="Первое сообщение").exists())
        self.assertTrue(lead.sources.filter(name="Клик по форме hero").exists())
        self.assertFalse(lead.sources.filter(name="Источник трафика: google").exists())

    def test_send_form_sets_yandex_as_primary_source_from_utm(self):
        response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Иван",
                        "phone": "+79990000000",
                        "company": "Acme",
                        "utm_data": {"utm_source": "yandex"},
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.get()
        client = Client.objects.get()

        self.assertIsNotNone(lead.source_id)
        self.assertEqual(lead.source.code, "traffic-source-yandex")
        self.assertEqual(client.source_id, lead.source_id)

    def test_deduplicates_lead_by_external_id(self):
        first_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "external_id": "chat-user-123",
                        "name": "Иван",
                        "phone": "+79990000000",
                    },
                }
            ),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "consultant",
                    "payload": {
                        "external_id": "chat-user-123",
                        "name": "Иван Петров",
                        "phone": "+79990000000",
                        "email": "ivan@example.com",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

        lead = Lead.objects.get()
        self.assertEqual(first_response.json()["crm_lead_id"], lead.id)
        self.assertEqual(second_response.json()["crm_lead_id"], lead.id)
        self.assertEqual(lead.external_id, "chat-user-123")
        self.assertEqual(lead.email, "ivan@example.com")

    def test_deduplicates_lead_by_normalized_phone(self):
        first_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Иван",
                        "phone": "+7 (999) 000-00-00",
                    },
                }
            ),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("send_form"),
            data=json.dumps(
                {
                    "form_type": "hero",
                    "payload": {
                        "name": "Иван",
                        "phone": "8 999 000 00 00",
                        "email": "ivan@example.com",
                    },
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

        lead = Lead.objects.get()
        self.assertEqual(first_response.json()["crm_lead_id"], lead.id)
        self.assertEqual(second_response.json()["crm_lead_id"], lead.id)
        self.assertEqual(lead.phone_normalized, "79990000000")
        self.assertEqual(lead.email, "ivan@example.com")

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
    @patch("main.views.send_form_to_telegram")
    @patch("main.views.Dadata")
    def test_telegram_and_submission_receive_enriched_company_payload(self, dadata_cls, send_telegram_mock):
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
                        ],
                        "management": {
                            "name": "Верхоланцев Никита Валерьевич",
                            "post": "ДИРЕКТОР",
                        },
                        "phones": [{"value": "+7 905 9405785"}],
                        "address": {"value": "г Омск, ул 22 Партсъезда, д 51Г, офис 4"},
                        "name": {
                            "full_with_opf": 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ЭНЕРГОЭКСПЕРТ"',
                            "short_with_opf": 'ООО "ЭНЕРГОЭКСПЕРТ"',
                        },
                    },
                }
            ]
        }
        send_telegram_mock.return_value = {"sent": 1, "total": 1, "errors": []}

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
        form_submission = FormSubmission.objects.get()
        self.assertEqual(form_submission.payload["company_inn"], "5503190710")
        self.assertEqual(form_submission.payload["company_kpp"], "550301001")
        self.assertEqual(form_submission.payload["company_address"], "г Омск, ул 22 Партсъезда, д 51Г, офис 4")
        self.assertEqual(
            form_submission.payload["company_industry"],
            "Производство прочих готовых металлических изделий",
        )

        send_telegram_mock.assert_called_once()
        telegram_payload = send_telegram_mock.call_args.kwargs["payload"]
        self.assertEqual(telegram_payload["company_inn"], "5503190710")
        self.assertEqual(telegram_payload["company_kpp"], "550301001")
        self.assertEqual(telegram_payload["company_ogrn"], "1205500003763")
        self.assertEqual(telegram_payload["company_okved"], "25.99")
        self.assertEqual(telegram_payload["company_director_name"], "Верхоланцев Никита Валерьевич")
        self.assertEqual(telegram_payload["company_director_phone"], "+7 905 9405785")

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
