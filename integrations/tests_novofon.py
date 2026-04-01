import json
from datetime import timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Contact, Deal, DealStage, Lead, TrafficSource
from integrations.models import (
    PhoneCall,
    PhoneCallDirection,
    PhoneCallStatus,
    PhoneCallTranscriptionStatus,
    TelephonyEventLog,
    TelephonyEventStatus,
    TelephonyProvider,
    TelephonyProviderAccount,
    TelephonyUserMapping,
)
from integrations.novofon.client import (
    DEFAULT_CALL_API_BASE_URL,
    DEFAULT_DATA_API_BASE_URL,
    NovofonClientError,
    NovofonClient,
)
from integrations.novofon.services import claim_novofon_events_for_processing
from integrations.novofon.security import build_novofon_webhook_signature
from integrations.novofon.selectors import normalize_phone


class NovofonPhoneNormalizationTests(SimpleTestCase):
    def test_normalizes_local_and_eight_prefixed_numbers(self):
        self.assertEqual(normalize_phone("+7 (900) 000-00-00"), "79000000000")
        self.assertEqual(normalize_phone("8 (900) 000-00-00"), "79000000000")
        self.assertEqual(normalize_phone("9000000000"), "79000000000")


class NovofonClientRoutingTests(SimpleTestCase):
    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def test_ping_uses_data_api_base_url(self):
        account = TelephonyProviderAccount(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_key="token-1",
            api_base_url="",
        )
        client = NovofonClient(account)
        request_mock = Mock(return_value=self._FakeResponse({"result": {"data": [{"id": 1}]}}))

        with patch("integrations.novofon.client.requests.post", request_mock):
            client.ping()

        self.assertEqual(request_mock.call_args.kwargs["url"], DEFAULT_DATA_API_BASE_URL)
        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "get.account")
        self.assertEqual(payload["params"]["access_token"], "token-1")

    def test_calls_report_uses_novofon_timezone_from_settings(self):
        account = TelephonyProviderAccount(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_key="token-1",
            api_base_url="",
            settings_json={"novofon_timezone": "Asia/Omsk"},
        )
        client = NovofonClient(account)
        request_mock = Mock(return_value=self._FakeResponse({"result": {"metadata": {}, "data": []}}))

        with patch("integrations.novofon.client.requests.post", request_mock):
            client.get_calls_report(
                date_from=timezone.datetime(2026, 3, 27, 0, 0, tzinfo=ZoneInfo("UTC")),
                date_till=timezone.datetime(2026, 3, 27, 1, 0, tzinfo=ZoneInfo("UTC")),
                limit=10,
                offset=0,
            )

        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "get.calls_report")
        self.assertEqual(payload["params"]["date_from"], "2026-03-27 06:00:00")
        self.assertEqual(payload["params"]["date_till"], "2026-03-27 07:00:00")

    def test_initiate_call_uses_call_api_and_virtual_number(self):
        account = TelephonyProviderAccount(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_key="token-2",
            api_base_url="",
            allowed_virtual_numbers=["+7 (495) 000-00-00"],
            settings_json={},
        )
        client = NovofonClient(account)

        def request_side_effect(*args, **kwargs):
            payload = kwargs["json"]
            if payload["method"] == "get.virtual_numbers":
                return self._FakeResponse({
                    "result": {
                        "data": [
                            {
                                "virtual_phone_number": "74950000000",
                                "status": "active",
                            }
                        ]
                    }
                })
            if payload["method"] == "start.employee_call":
                return self._FakeResponse({"result": {"data": {"call_session_id": 12345}}})
            raise AssertionError(f"Unexpected method {payload['method']}")

        request_mock = Mock(side_effect=request_side_effect)
        with patch("integrations.novofon.client.requests.post", request_mock):
            response = client.initiate_call(
                employee_id="25",
                extension="101",
                phone="+7 900 000-00-00",
                comment="Перезвонить",
                external_context={"phone_call_id": 77},
            )

        self.assertEqual(response["call_session_id"], 12345)
        self.assertEqual(request_mock.call_args.kwargs["url"], DEFAULT_CALL_API_BASE_URL)
        payload = request_mock.call_args.kwargs["json"]
        self.assertEqual(payload["method"], "start.employee_call")
        self.assertEqual(payload["params"]["virtual_phone_number"], "74950000000")
        self.assertEqual(payload["params"]["contact"], "79000000000")
        self.assertEqual(payload["params"]["employee"]["id"], 25)
        self.assertEqual(payload["params"]["external_id"], "crm_phone_call_77")


class NovofonWebhookApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="novofon_manager",
            password="testpass123",
            is_staff=True,
        )
        self.account = TelephonyProviderAccount.objects.create(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            webhook_shared_secret="secret",
            default_owner=self.user,
        )
        self.mapping = TelephonyUserMapping.objects.create(
            provider_account=self.account,
            crm_user=self.user,
            novofon_employee_id="emp-1",
            novofon_extension="101",
            novofon_full_name="Manager One",
            is_active=True,
        )
        self.company = Client.objects.create(name="Acme", phone="+7 900 000-00-00")
        self.contact = Contact.objects.create(
            client=self.company,
            first_name="Иван",
            phone="+7 (900) 000-00-00",
            is_primary=True,
        )
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress_novofon",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Сделка по звонку",
            stage=self.stage,
            client=self.company,
            owner=self.user,
        )

    def _payload(self, *, event_id="event-1"):
        now = timezone.now()
        return {
            "event_type": "call_completed",
            "event_id": event_id,
            "call_id": "call-1",
            "direction": "inbound",
            "status": "completed",
            "from": "+7 (900) 000-00-00",
            "to": "+7 (495) 000-00-00",
            "employee_id": "emp-1",
            "started_at": now.isoformat(),
            "ended_at": now.isoformat(),
            "duration": 42,
        }

    def _signed_payload(self, *, event="NOTIFY_END", pbx_call_id="pbx-1"):
        call_start = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "event": event,
            "pbx_call_id": pbx_call_id,
            "caller_id": "+7 (900) 000-00-00",
            "called_did": "+7 (495) 000-00-00",
            "call_start": call_start,
            "notification_time": call_start,
            "disposition": "answered",
            "duration": 42,
            "internal": "101",
        }

    def test_webhook_creates_phone_call_and_links_entities(self):
        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        event = TelephonyEventLog.objects.get(pk=response.data["event_id"])
        self.assertEqual(event.status, TelephonyEventStatus.PROCESSED)
        self.assertTrue(response.data["processed_immediately"])

        call = PhoneCall.objects.get(external_call_id="call-1")
        self.assertEqual(call.contact_id, self.contact.pk)
        self.assertEqual(call.company_id, self.company.pk)
        self.assertEqual(call.deal_id, self.deal.pk)
        self.assertEqual(call.responsible_user_id, self.user.pk)
        self.assertEqual(call.client_phone_normalized, "79000000000")
        event.refresh_from_db()
        self.assertEqual(event.status, TelephonyEventStatus.PROCESSED)

    def test_duplicate_webhook_is_marked_and_does_not_duplicate_call(self):
        first_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-dup"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        self.assertEqual(first_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())
        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-dup"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        self.assertEqual(PhoneCall.objects.filter(external_call_id="call-1").count(), 1)
        statuses = list(TelephonyEventLog.objects.order_by("id").values_list("status", flat=True))
        self.assertEqual(statuses, [TelephonyEventStatus.PROCESSED, TelephonyEventStatus.IGNORED_DUPLICATE])

    def test_webhook_accepts_raw_json_body_with_non_json_content_type(self):
        response = self.client.generic(
            "POST",
            reverse("integrations-novofon-webhook"),
            data=json.dumps(self._payload(event_id="event-raw-json")),
            content_type="text/plain",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(TelephonyEventLog.objects.filter(external_event_id="event-raw-json").exists())

    def test_webhook_accepts_embedded_json_payload_wrapped_as_single_key(self):
        raw_payload = (
            '{\n'
            '  "event_type": ""in_call_session"",\n'
            '  "call_session_id": "187020303",\n'
            '  "communication_id": "12323",\n'
            '  "direction": ""in"",\n'
            '  "calling_phone_number": ""79260000001"",\n'
            '  "called_phone_number": ""79260000002"",\n'
            '  "contact_phone_number": ""79000000000"",\n'
            '  "communication_number": "1",\n'
            '  "virtual_phone_number": ""74950000000"",\n'
            '  "notification_time": ""2026-03-28 16:30:00"",\n'
            '  "start_time": ""2026-03-28 16:29:07"",\n'
            '  "external_id": ""t456uy""\n'
            '}'
        )
        wrapped_payload = json.dumps({raw_payload: ""}, ensure_ascii=False)

        response = self.client.generic(
            "POST",
            reverse("integrations-novofon-webhook"),
            data=wrapped_payload,
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        event = TelephonyEventLog.objects.get(pk=response.data["event_id"])
        self.assertEqual(event.external_call_id, "187020303")
        self.assertEqual(event.event_type, "in_call_session")

    def test_webhook_accepts_valid_signature_and_processes_official_payload(self):
        self.account.api_secret = "api-secret"
        self.account.webhook_shared_secret = ""
        self.account.save(update_fields=["api_secret", "webhook_shared_secret"])
        payload = self._signed_payload()
        signature = build_novofon_webhook_signature(payload, secret=self.account.api_secret)

        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            payload,
            format="json",
            HTTP_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        call = PhoneCall.objects.get(external_call_id="pbx-1")
        self.assertEqual(call.status, "answered")
        self.assertEqual(call.direction, "inbound")
        self.assertEqual(call.phone_from, "+7 (900) 000-00-00")
        self.assertEqual(call.phone_to, "+7 (495) 000-00-00")
        self.assertEqual(call.responsible_user_id, self.user.pk)

    def test_webhook_uses_novofon_timezone_for_naive_official_timestamps(self):
        self.account.api_secret = "api-secret"
        self.account.webhook_shared_secret = ""
        self.account.settings_json = {"novofon_timezone": "Asia/Omsk"}
        self.account.save(update_fields=["api_secret", "webhook_shared_secret", "settings_json", "updated_at"])
        payload = self._signed_payload(event="NOTIFY_START", pbx_call_id="pbx-tz-1")
        payload["call_start"] = "2026-04-01 18:43:00"
        payload["notification_time"] = "2026-04-01 18:43:00"
        signature = build_novofon_webhook_signature(payload, secret=self.account.api_secret)

        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            payload,
            format="json",
            HTTP_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        call = PhoneCall.objects.get(external_call_id="pbx-tz-1")
        self.assertEqual(timezone.localtime(call.started_at, ZoneInfo("Asia/Omsk")).strftime("%Y-%m-%d %H:%M:%S"), "2026-04-01 18:43:00")

    def test_webhook_rejects_missing_signature_when_api_secret_configured(self):
        self.account.api_secret = "api-secret"
        self.account.webhook_shared_secret = ""
        self.account.save(update_fields=["api_secret", "webhook_shared_secret"])

        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._signed_payload(pbx_call_id="pbx-missing-signature"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "missing_signature")
        self.assertFalse(TelephonyEventLog.objects.filter(external_call_id="pbx-missing-signature").exists())

    def test_webhook_rejects_invalid_signature_when_api_secret_configured(self):
        self.account.api_secret = "api-secret"
        self.account.webhook_shared_secret = ""
        self.account.save(update_fields=["api_secret", "webhook_shared_secret"])

        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._signed_payload(pbx_call_id="pbx-invalid-signature"),
            format="json",
            HTTP_SIGNATURE="invalid-signature",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "invalid_signature")
        self.assertFalse(TelephonyEventLog.objects.filter(external_call_id="pbx-invalid-signature").exists())

    def test_reprocess_endpoint_requeues_failed_event(self):
        event = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_event_id="event-failed",
            external_call_id="call-failed",
            deduplication_key="dedupe-failed",
            payload_json=self._payload(event_id="event-failed"),
            headers_json={"X-Webhook-Secret": "secret"},
            status=TelephonyEventStatus.FAILED,
            error_text="boom",
            retry_count=2,
        )

        response = self.client.post(reverse("telephony-event-reprocess", kwargs={"pk": event.pk}))

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        event.refresh_from_db()
        self.assertEqual(event.status, TelephonyEventStatus.QUEUED)
        self.assertEqual(event.retry_count, 2)
        self.assertEqual(event.error_text, "")

    def test_recording_event_updates_existing_call_recording_url(self):
        initial_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-call-finished"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        self.assertEqual(initial_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        recording_payload = {
            "event": "RECORD_CALL",
            "event_id": "event-record-1",
            "call_session_id": "call-1",
            "call_record_file_info": {
                "file_link": "https://media.novofon.ru/records/call-1.mp3",
            },
        }
        recording_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            recording_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(recording_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        call = PhoneCall.objects.get(external_call_id="call-1")
        self.assertEqual(call.status, PhoneCallStatus.COMPLETED)
        self.assertEqual(call.direction, PhoneCallDirection.INBOUND)
        self.assertEqual(call.recording_url, "https://media.novofon.ru/records/call-1.mp3")

    @override_settings(
        SONIOX_API_KEY="soniox-key",
        CRM_PUBLIC_BASE_URL="https://crm.example.test",
        SONIOX_WEBHOOK_SECRET="soniox-secret",
    )
    @patch("integrations.soniox.client.requests.request")
    def test_recording_event_submits_transcription_to_soniox(self, request_mock):
        initial_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-call-with-transcript"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        self.assertEqual(initial_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        soniox_response = Mock()
        soniox_response.raise_for_status.return_value = None
        soniox_response.json.return_value = {"id": "tr-call-1", "status": "queued"}
        request_mock.return_value = soniox_response

        recording_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            {
                "event": "RECORD_CALL",
                "event_id": "event-record-transcript-1",
                "call_session_id": "call-1",
                "call_record_file_info": {
                    "file_link": "https://media.novofon.ru/records/call-1.mp3",
                },
            },
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(recording_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        call = PhoneCall.objects.get(external_call_id="call-1")
        self.assertEqual(call.transcription_status, PhoneCallTranscriptionStatus.QUEUED)
        self.assertEqual(call.transcription_external_id, "tr-call-1")
        self.assertEqual(call.transcription_recording_url, "https://media.novofon.ru/records/call-1.mp3")
        request_kwargs = request_mock.call_args.kwargs
        self.assertEqual(request_kwargs["method"], "POST")
        self.assertEqual(request_kwargs["url"], "https://api.soniox.com/v1/transcriptions")
        self.assertEqual(request_kwargs["json"]["audio_url"], "https://media.novofon.ru/records/call-1.mp3")
        self.assertEqual(request_kwargs["json"]["model"], "stt-async-v4")
        self.assertEqual(request_kwargs["json"]["language_hints"], ["ru"])
        self.assertTrue(request_kwargs["json"]["language_hints_strict"])
        self.assertEqual(
            request_kwargs["json"]["webhook"]["url"],
            "https://crm.example.test/api/integrations/soniox/webhook/",
        )
        self.assertEqual(
            request_kwargs["json"]["webhook"]["headers"]["X-Soniox-Webhook-Secret"],
            "soniox-secret",
        )

    @override_settings(SONIOX_API_KEY="soniox-key")
    @patch("integrations.soniox.client.requests.request")
    def test_recording_event_completes_ringing_call_and_submits_transcription(self, request_mock):
        ringing_payload = self._payload(event_id="event-ringing-call")
        ringing_payload["event_type"] = "in_call_session"
        ringing_payload["status"] = "ringing"
        ringing_payload["ended_at"] = ""
        ringing_payload["duration"] = 0

        initial_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            ringing_payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        self.assertEqual(initial_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        soniox_response = Mock()
        soniox_response.raise_for_status.return_value = None
        soniox_response.json.return_value = {"id": "tr-ringing-call-1", "status": "queued"}
        request_mock.return_value = soniox_response

        recording_response = self.client.post(
            reverse("integrations-novofon-webhook"),
            {
                "event": "RECORD_CALL",
                "event_id": "event-record-ringing-1",
                "call_session_id": "call-1",
                "call_record_file_info": {
                    "file_link": "https://media.novofon.ru/records/call-1.mp3",
                },
            },
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(recording_response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        call = PhoneCall.objects.get(external_call_id="call-1")
        self.assertEqual(call.status, PhoneCallStatus.COMPLETED)
        self.assertEqual(call.transcription_status, PhoneCallTranscriptionStatus.QUEUED)
        self.assertEqual(call.transcription_external_id, "tr-ringing-call-1")

    def test_queue_processor_handles_embedded_json_payload_saved_in_event_log(self):
        wrapped_payload = {
            '{\n  "event_type": ""in_call_session"",\n  "call_session_id": "187020303",\n  "communication_id": "12323",\n  "direction": ""in"",\n  "calling_phone_number": ""79000000000"",\n  "called_phone_number": ""74950000000"",\n  "contact_phone_number": ""79000000000"",\n  "communication_number": "1",\n  "virtual_phone_number": ""74950000000"",\n  "notification_time": ""2026-03-28 16:30:00"",\n  "start_time": ""2026-03-28 16:29:07""\n}': ""
        }
        event = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="",
            external_event_id="",
            external_call_id="",
            deduplication_key="embedded-json-payload",
            payload_json=wrapped_payload,
            headers_json={"Content-Type": "application/json"},
            status=TelephonyEventStatus.QUEUED,
        )

        result = call_command("process_novofon_webhook_queue", stdout=StringIO())
        self.assertIsNone(result)
        event.refresh_from_db()
        self.assertEqual(event.status, TelephonyEventStatus.PROCESSED)
        call = PhoneCall.objects.get(external_call_id="187020303")
        self.assertEqual(call.direction, PhoneCallDirection.INBOUND)

    def test_webhook_creates_unknown_lead_with_phone_source(self):
        self.account.create_lead_for_unknown_number = True
        self.account.save(update_fields=["create_lead_for_unknown_number", "updated_at"])

        payload = self._payload(event_id="event-phone-source")
        payload["call_id"] = "call-phone-source"
        payload["from"] = "+7 (901) 111-22-33"

        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            payload,
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        call = PhoneCall.objects.get(external_call_id="call-phone-source")
        self.assertIsNotNone(call.lead_id)
        self.assertEqual(call.lead.source.code, "phone")
        self.assertEqual(call.lead.source.name, "Телефон")
        self.assertTrue(TrafficSource.objects.filter(code="phone").exists())


class NovofonCallApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="novofon_caller",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.account = TelephonyProviderAccount.objects.create(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_base_url="https://api.example.test",
        )
        self.lead = Lead.objects.create(title="Lead call", phone="+7 900 000-00-00")

    def test_call_requires_user_mapping(self):
        response = self.client.post(
            reverse("telephony-novofon-call"),
            {
                "phone": "+7 900 000-00-00",
                "entity_type": "lead",
                "entity_id": self.lead.pk,
                "comment": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("сопоставление", response.data["error"].lower())

    @patch("integrations.novofon.services.NovofonClient.initiate_call")
    def test_call_endpoint_creates_outbound_phone_call(self, initiate_call_mock):
        TelephonyUserMapping.objects.create(
            provider_account=self.account,
            crm_user=self.user,
            novofon_employee_id="25",
            novofon_extension="102",
            novofon_full_name="Caller Two",
            is_active=True,
        )
        initiate_call_mock.return_value = {"call_id": "out-call-1", "status": "created"}

        response = self.client.post(
            reverse("telephony-novofon-call"),
            {
                "phone": "+7 900 000-00-00",
                "entity_type": "lead",
                "entity_id": self.lead.pk,
                "comment": "Перезвонить",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        call = PhoneCall.objects.get(external_call_id="out-call-1")
        self.assertEqual(call.direction, "outbound")


class PhoneCallApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="phone_call_api_user",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="API Company", phone="+7 900 000-00-00")

    @patch("integrations.novofon.views.refresh_phone_call_transcription")
    def test_call_list_refreshes_pending_transcription(self, refresh_transcription_mock):
        call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="api-call-1",
            direction=PhoneCallDirection.INBOUND,
            status=PhoneCallStatus.COMPLETED,
            phone_from="+7 900 000-00-00",
            phone_to="+7 495 000-00-00",
            company=self.company,
            recording_url="https://media.novofon.ru/records/api-call-1.mp3",
            transcription_status=PhoneCallTranscriptionStatus.QUEUED,
            transcription_external_id="tr-api-call-1",
        )

        def refresh_side_effect(target_call):
            target_call.transcription_status = PhoneCallTranscriptionStatus.COMPLETED
            target_call.transcription_text = "Текст подтянулся через API."
            target_call.save(update_fields=["transcription_status", "transcription_text", "updated_at"])
            return {"ok": True, "status": PhoneCallTranscriptionStatus.COMPLETED, "completed": True}

        refresh_transcription_mock.side_effect = refresh_side_effect

        response = self.client.get(
            reverse("telephony-calls"),
            {"entity_type": "company", "entity_id": self.company.pk, "page_size": 10},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["transcription_status"], PhoneCallTranscriptionStatus.COMPLETED)
        self.assertEqual(response.data["results"][0]["transcription_text"], "Текст подтянулся через API.")
        refresh_transcription_mock.assert_called_once()


class IncomingPhoneCallPopupApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="incoming_popup_user",
            password="testpass123",
            is_staff=True,
        )
        self.other_user = get_user_model().objects.create_user(
            username="incoming_popup_other",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="Popup Co", phone="+7 900 111-22-33")
        self.lead = Lead.objects.create(title="Popup Lead", phone="+7 900 111-22-33", assigned_to=self.user, client=self.company)
        self.stage = DealStage.objects.create(
            name="Popup Stage",
            code="popup_stage",
            order=20,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="Popup Deal",
            client=self.company,
            lead=self.lead,
            stage=self.stage,
            owner=self.user,
        )

    def test_initial_popup_poll_only_primes_cursor(self):
        call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="popup-call-1",
            direction="inbound",
            status="ringing",
            phone_from="+7 900 111-22-33",
            phone_to="+7 495 111-22-33",
            responsible_user=self.user,
            company=self.company,
            lead=self.lead,
            deal=self.deal,
        )

        response = self.client.get(reverse("telephony-incoming-call-popup"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["next_call_id"], call.pk)

    def test_popup_poll_returns_only_new_inbound_calls_for_current_user(self):
        first_call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="popup-call-2",
            direction="inbound",
            status="ringing",
            phone_from="+7 900 111-22-33",
            phone_to="+7 495 111-22-33",
            responsible_user=self.user,
            company=self.company,
            lead=self.lead,
            deal=self.deal,
        )
        PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="popup-call-outbound",
            direction="outbound",
            status="ringing",
            phone_from="101",
            phone_to="+7 900 111-22-33",
            responsible_user=self.user,
        )
        PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="popup-call-other-user",
            direction="inbound",
            status="ringing",
            phone_from="+7 900 444-55-66",
            phone_to="+7 495 111-22-33",
            responsible_user=self.other_user,
        )
        second_call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="popup-call-3",
            direction="inbound",
            status="answered",
            phone_from="+7 900 111-22-33",
            phone_to="+7 495 111-22-33",
            responsible_user=self.user,
            company=self.company,
            lead=self.lead,
            deal=self.deal,
        )

        response = self.client.get(reverse("telephony-incoming-call-popup"), {"after_id": first_call.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["id"], second_call.pk)
        self.assertEqual(response.data["items"][0]["target_entity_type"], "deal")
        self.assertEqual(response.data["items"][0]["target_entity_id"], self.deal.pk)
        self.assertEqual(response.data["next_call_id"], second_call.pk)


class NovofonWebhookQueueClaimTests(APITestCase):
    def test_failed_event_respects_backoff_before_reclaim(self):
        recent_failed = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="failed-recent",
            status=TelephonyEventStatus.FAILED,
            retry_count=1,
            processed_at=timezone.now(),
        )
        ready_failed = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="failed-ready",
            status=TelephonyEventStatus.FAILED,
            retry_count=1,
            processed_at=timezone.now() - timedelta(seconds=45),
        )

        claimed = claim_novofon_events_for_processing(
            limit=10,
            retry_failed=True,
            failed_backoff_base_seconds=30,
            failed_backoff_max_seconds=300,
            reclaim_stale_processing_after_seconds=0,
        )

        self.assertEqual([event.pk for event in claimed], [ready_failed.pk])
        recent_failed.refresh_from_db()
        ready_failed.refresh_from_db()
        self.assertEqual(recent_failed.status, TelephonyEventStatus.FAILED)
        self.assertEqual(ready_failed.status, TelephonyEventStatus.PROCESSING)

    def test_stale_processing_event_is_reclaimed(self):
        stale_processing = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="processing-stale",
            status=TelephonyEventStatus.PROCESSING,
            retry_count=1,
            processed_at=timezone.now() - timedelta(minutes=10),
        )

        claimed = claim_novofon_events_for_processing(
            limit=10,
            retry_failed=False,
            reclaim_stale_processing_after_seconds=300,
        )

        self.assertEqual([event.pk for event in claimed], [stale_processing.pk])
        stale_processing.refresh_from_db()
        self.assertEqual(stale_processing.status, TelephonyEventStatus.PROCESSING)
        self.assertEqual(stale_processing.retry_count, 2)
        self.assertIsNotNone(stale_processing.processed_at)


class TelephonyHealthApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="telephony_health_admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_health_endpoint_returns_queue_counts_and_problem_events(self):
        failed_event = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="health-failed",
            status=TelephonyEventStatus.FAILED,
            error_text="broken payload",
            retry_count=2,
            processed_at=timezone.now() - timedelta(minutes=2),
        )
        stale_processing = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="health-processing",
            status=TelephonyEventStatus.PROCESSING,
            retry_count=1,
            processed_at=timezone.now() - timedelta(minutes=10),
        )
        queued_event = TelephonyEventLog.objects.create(
            provider=TelephonyProvider.NOVOFON,
            event_type="call_completed",
            external_call_id="health-queued",
            status=TelephonyEventStatus.QUEUED,
        )

        response = self.client.get(reverse("telephony-health"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["queued"], 1)
        self.assertEqual(response.data["counts"]["failed"], 1)
        self.assertEqual(response.data["counts"]["processing"], 1)
        self.assertEqual(response.data["counts"]["stale_processing"], 1)
        returned_event_ids = {item["id"] for item in response.data["problem_events"]}
        self.assertIn(failed_event.pk, returned_event_ids)
        self.assertIn(stale_processing.pk, returned_event_ids)
        self.assertIn(queued_event.pk, returned_event_ids)
        stale_item = next(item for item in response.data["problem_events"] if item["id"] == stale_processing.pk)
        self.assertEqual(stale_item["is_stale_processing"], True)


class NovofonSyncEmployeesApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="novofon_admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.account = TelephonyProviderAccount.objects.create(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_base_url="https://api.example.test",
        )

    @patch("integrations.novofon.services.NovofonClient.list_employees")
    def test_sync_employees_creates_mappings(self, list_employees_mock):
        list_employees_mock.return_value = [
            {
                "id": "emp-1",
                "extension": "101",
                "full_name": "Alice Example",
                "is_active": True,
            }
        ]

        response = self.client.post(reverse("telephony-novofon-sync-employees"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mapping = TelephonyUserMapping.objects.get(provider_account=self.account, novofon_employee_id="emp-1")
        self.assertEqual(mapping.novofon_extension, "101")
        self.assertEqual(mapping.novofon_full_name, "Alice Example")

    @patch("integrations.novofon.services.NovofonClient.list_employees")
    def test_sync_employees_uses_nested_extension_payload_instead_of_stringifying_object(self, list_employees_mock):
        list_employees_mock.return_value = [
            {
                "id": "emp-2",
                "extension": {
                    "extension_phone_number": "102",
                    "inner_phone_number": "202",
                    "unexpected_payload": "x" * 300,
                },
                "full_name": "Bob Example",
                "is_active": True,
            }
        ]

        response = self.client.post(reverse("telephony-novofon-sync-employees"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mapping = TelephonyUserMapping.objects.get(provider_account=self.account, novofon_employee_id="emp-2")
        self.assertEqual(mapping.novofon_extension, "102")
        self.assertEqual(mapping.novofon_full_name, "Bob Example")

    @patch("integrations.novofon.services.NovofonClient.list_employees")
    def test_sync_employees_returns_api_error_instead_of_http_500(self, list_employees_mock):
        list_employees_mock.side_effect = NovofonClientError("Метод get.employees недоступен для текущего токена.")

        response = self.client.post(reverse("telephony-novofon-sync-employees"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["ok"], False)
        self.assertIn("get.employees", response.data["error"])

    @patch("integrations.novofon.views.sync_novofon_employees")
    def test_sync_employees_returns_json_for_unexpected_error(self, sync_novofon_employees_mock):
        sync_novofon_employees_mock.side_effect = RuntimeError("boom")

        response = self.client.post(reverse("telephony-novofon-sync-employees"))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["ok"], False)
        self.assertEqual(response.data["error"], "boom")


class NovofonSettingsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="novofon_settings_admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.account = TelephonyProviderAccount.objects.create(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_key="visible-only-in-admin",
            api_secret="secret-token",
            api_base_url="https://dataapi-jsonrpc.novofon.ru/v2.0",
            webhook_shared_secret="webhook-secret",
            default_owner=self.user,
            allowed_virtual_numbers=["74950000000"],
            create_task_for_missed_call=True,
            link_calls_to_open_deal_only=True,
        )
        self.mapping = TelephonyUserMapping.objects.create(
            provider_account=self.account,
            crm_user=self.user,
            novofon_employee_id="emp-1",
            novofon_extension="101",
            novofon_full_name="Alice Example",
            is_active=True,
        )

    def test_settings_response_hides_secret_fields(self):
        response = self.client.get(reverse("telephony-novofon-settings"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("api_key", response.data)
        self.assertNotIn("api_secret", response.data)
        self.assertNotIn("webhook_shared_secret", response.data)
        self.assertTrue(response.data["has_api_secret"])
        self.assertEqual(len(response.data["mappings"]), 1)

    def test_settings_update_preserves_secret_fields_when_omitted(self):
        response = self.client.put(
            reverse("telephony-novofon-settings"),
            {
                "enabled": False,
                "api_base_url": "https://dataapi-jsonrpc.novofon.ru/v2.0",
                "webhook_path": "/api/integrations/novofon/webhook/",
                "default_owner": self.user.pk,
                "create_lead_for_unknown_number": True,
                "create_task_for_missed_call": False,
                "link_calls_to_open_deal_only": False,
                "allowed_virtual_numbers": ["74951112233", "74954445566"],
                "is_debug_logging_enabled": True,
                "settings_json": {"novofon_timezone": "Asia/Omsk"},
                "mappings": [
                    {
                        "id": self.mapping.pk,
                        "crm_user": self.user.pk,
                        "novofon_employee_id": "emp-1",
                        "novofon_extension": "102",
                        "novofon_full_name": "Alice Updated",
                        "is_active": True,
                        "is_default_owner": True,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.mapping.refresh_from_db()
        self.assertEqual(self.account.api_key, "visible-only-in-admin")
        self.assertEqual(self.account.api_secret, "secret-token")
        self.assertEqual(self.account.webhook_shared_secret, "webhook-secret")
        self.assertFalse(self.account.enabled)
        self.assertTrue(self.account.create_lead_for_unknown_number)
        self.assertFalse(self.account.create_task_for_missed_call)
        self.assertFalse(self.account.link_calls_to_open_deal_only)
        self.assertEqual(self.account.allowed_virtual_numbers, ["74951112233", "74954445566"])
        self.assertTrue(self.account.is_debug_logging_enabled)
        self.assertEqual(self.mapping.novofon_extension, "102")
        self.assertEqual(self.mapping.novofon_full_name, "Alice Updated")
        self.assertTrue(self.mapping.is_default_owner)


class NovofonImportCallsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="novofon_history_admin",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.account = TelephonyProviderAccount.objects.create(
            provider=TelephonyProvider.NOVOFON,
            enabled=True,
            api_key="token",
            api_base_url="https://dataapi-jsonrpc.novofon.ru/v2.0",
        )
        TelephonyUserMapping.objects.create(
            provider_account=self.account,
            crm_user=self.user,
            novofon_employee_id="101",
            novofon_extension="101",
            novofon_full_name="Alice Example",
            is_active=True,
        )
        self.company = Client.objects.create(name="History Co", phone="+7 900 000-00-00")
        self.contact = Contact.objects.create(
            client=self.company,
            first_name="История",
            phone="+7 900 000-00-00",
            is_primary=True,
        )
        self.lead = Lead.objects.create(
            title="Исторический лид",
            phone="+7 900 000-00-00",
            assigned_to=self.user,
        )
        self.stage = DealStage.objects.create(
            name="History Stage",
            code="history_stage",
            order=10,
            is_active=True,
            is_final=False,
        )
        self.deal = Deal.objects.create(
            title="History Deal",
            client=self.company,
            lead=self.lead,
            stage=self.stage,
            owner=self.user,
        )

    @patch("integrations.novofon.services.NovofonClient.get_calls_report")
    def test_import_calls_creates_phone_call_and_links_lead(self, get_calls_report_mock):
        now = timezone.now()
        get_calls_report_mock.side_effect = [
            {
                "metadata": {"total_items": 1},
                "data": [
                    {
                        "id": 555001,
                        "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "finish_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "direction": "in",
                        "is_lost": False,
                        "contact_phone_number": "+7 900 000-00-00",
                        "virtual_phone_number": "+7 495 000-00-00",
                        "operator_phone_number": "101",
                        "talk_duration": 45,
                        "clean_talk_duration": 40,
                        "total_duration": 50,
                        "full_record_file_link": "https://media.novofon.ru/1/abc",
                        "communication_id": 7001,
                        "last_answered_employee_id": "101",
                        "employees": [{"employee_id": "101"}],
                    }
                ],
            },
            {
                "metadata": {"total_items": 1},
                "data": [],
            },
        ]

        response = self.client.post(
            reverse("telephony-novofon-import-calls"),
            {"days": 7, "limit": 100, "max_records": 100},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["created"], 1)
        call = PhoneCall.objects.get(external_call_id="555001")
        self.assertEqual(call.lead_id, self.lead.pk)
        self.assertEqual(call.company_id, self.company.pk)
        self.assertEqual(call.contact_id, self.contact.pk)
        self.assertEqual(call.deal_id, self.deal.pk)
        self.assertEqual(call.crm_user_id, self.user.pk)

    @override_settings(SONIOX_API_KEY="soniox-key")
    @patch("integrations.soniox.client.requests.request")
    @patch("integrations.novofon.services.NovofonClient.get_calls_report")
    def test_import_calls_submits_transcription_when_recording_exists(self, get_calls_report_mock, request_mock):
        now = timezone.now()
        get_calls_report_mock.side_effect = [
            {
                "metadata": {"total_items": 1},
                "data": [
                    {
                        "id": 555010,
                        "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "finish_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "direction": "in",
                        "is_lost": False,
                        "contact_phone_number": "+7 900 000-00-00",
                        "virtual_phone_number": "+7 495 000-00-00",
                        "operator_phone_number": "101",
                        "talk_duration": 45,
                        "clean_talk_duration": 40,
                        "total_duration": 50,
                        "full_record_file_link": "https://media.novofon.ru/1/transcribe-me",
                        "communication_id": 7010,
                        "last_answered_employee_id": "101",
                        "employees": [{"employee_id": "101"}],
                    }
                ],
            },
            {"metadata": {"total_items": 1}, "data": []},
        ]
        soniox_response = Mock()
        soniox_response.raise_for_status.return_value = None
        soniox_response.json.return_value = {"id": "tr-history-1", "status": "queued"}
        request_mock.return_value = soniox_response

        response = self.client.post(
            reverse("telephony-novofon-import-calls"),
            {"days": 7, "limit": 100, "max_records": 100},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call = PhoneCall.objects.get(external_call_id="555010")
        self.assertEqual(call.transcription_status, PhoneCallTranscriptionStatus.QUEUED)
        self.assertEqual(call.transcription_external_id, "tr-history-1")

    @patch("integrations.novofon.services.NovofonClient.get_calls_report")
    def test_import_calls_backfills_missing_lead_for_existing_phone_call(self, get_calls_report_mock):
        now = timezone.now()
        existing_call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="555002",
            direction="inbound",
            status="completed",
            phone_from="+7 900 000-00-00",
            phone_to="+7 495 000-00-00",
            client_phone_normalized="79000000000",
            contact=self.contact,
            company=self.company,
            deal=self.deal,
        )
        self.assertIsNone(existing_call.lead_id)

        get_calls_report_mock.side_effect = [
            {
                "metadata": {"total_items": 1},
                "data": [
                    {
                        "id": 555002,
                        "start_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "finish_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "direction": "in",
                        "is_lost": False,
                        "contact_phone_number": "+7 900 000-00-00",
                        "virtual_phone_number": "+7 495 000-00-00",
                        "operator_phone_number": "101",
                        "talk_duration": 45,
                        "clean_talk_duration": 40,
                        "total_duration": 50,
                        "full_record_file_link": "https://media.novofon.ru/1/xyz",
                        "communication_id": 7002,
                        "last_answered_employee_id": "101",
                        "employees": [{"employee_id": "101"}],
                    }
                ],
            },
            {
                "metadata": {"total_items": 1},
                "data": [],
            },
        ]

        response = self.client.post(
            reverse("telephony-novofon-import-calls"),
            {"days": 7, "limit": 100, "max_records": 100},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        existing_call.refresh_from_db()
        self.assertEqual(existing_call.lead_id, self.lead.pk)

    @patch("integrations.novofon.services.NovofonClient.get_calls_report")
    def test_import_calls_uses_novofon_timezone_for_naive_timestamps(self, get_calls_report_mock):
        self.account.settings_json = {"novofon_timezone": "Asia/Omsk"}
        self.account.save(update_fields=["settings_json", "updated_at"])
        get_calls_report_mock.side_effect = [
            {
                "metadata": {"total_items": 1},
                "data": [
                    {
                        "id": 555003,
                        "start_time": "2026-03-27 12:00:00",
                        "finish_time": "2026-03-27 12:10:00",
                        "direction": "in",
                        "is_lost": False,
                        "contact_phone_number": "+7 900 000-00-00",
                        "virtual_phone_number": "+7 495 000-00-00",
                        "operator_phone_number": "101",
                        "talk_duration": 60,
                        "clean_talk_duration": 60,
                        "total_duration": 600,
                        "communication_id": 7003,
                        "last_answered_employee_id": "101",
                        "employees": [{"employee_id": "101"}],
                    }
                ],
            },
            {"metadata": {"total_items": 1}, "data": []},
        ]

        response = self.client.post(
            reverse("telephony-novofon-import-calls"),
            {"days": 7, "limit": 100, "max_records": 100},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call = PhoneCall.objects.get(external_call_id="555003")
        self.assertEqual(timezone.localtime(call.started_at, ZoneInfo("Asia/Omsk")).strftime("%Y-%m-%d %H:%M:%S"), "2026-03-27 12:00:00")


class SonioxWebhookApiTests(APITestCase):
    @override_settings(SONIOX_API_KEY="soniox-key", SONIOX_WEBHOOK_SECRET="soniox-secret")
    @patch("integrations.soniox.client.requests.request")
    def test_webhook_completes_phone_call_transcription(self, request_mock):
        call = PhoneCall.objects.create(
            provider=TelephonyProvider.NOVOFON,
            external_call_id="call-soniox-1",
            direction=PhoneCallDirection.INBOUND,
            status=PhoneCallStatus.COMPLETED,
            phone_from="+7 900 000-00-00",
            phone_to="+7 495 000-00-00",
            recording_url="https://media.novofon.ru/records/call-soniox-1.mp3",
            transcription_status=PhoneCallTranscriptionStatus.PROCESSING,
            transcription_external_id="tr-soniox-1",
            transcription_recording_url="https://media.novofon.ru/records/call-soniox-1.mp3",
            transcription_requested_at=timezone.now(),
        )

        status_response = Mock()
        status_response.raise_for_status.return_value = None
        status_response.json.return_value = {"id": "tr-soniox-1", "status": "completed"}
        transcript_response = Mock()
        transcript_response.raise_for_status.return_value = None
        transcript_response.json.return_value = {"text": "Добрый день, запись успешно распознана"}
        request_mock.side_effect = [status_response, transcript_response]

        response = self.client.post(
            reverse("integrations-soniox-webhook"),
            {"id": "tr-soniox-1", "status": "completed"},
            format="json",
            HTTP_X_SONIOX_WEBHOOK_SECRET="soniox-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        call.refresh_from_db()
        self.assertEqual(call.transcription_status, PhoneCallTranscriptionStatus.COMPLETED)
        self.assertEqual(call.transcription_text, "Добрый день, запись успешно распознана")
        self.assertIsNotNone(call.transcription_completed_at)
        self.assertEqual(request_mock.call_count, 2)
