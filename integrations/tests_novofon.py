from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Contact, Deal, DealStage, Lead
from integrations.models import (
    PhoneCall,
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
                employee_id="emp-1",
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
        self.assertEqual(payload["params"]["employee"]["id"], "emp-1")
        self.assertEqual(payload["params"]["employee"]["phone_number"], "101")
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
        self.assertEqual(event.status, TelephonyEventStatus.QUEUED)
        self.assertFalse(PhoneCall.objects.filter(external_call_id="call-1").exists())

        out = StringIO()
        call_command("process_novofon_webhook_queue", stdout=out)

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
        call_command("process_novofon_webhook_queue", stdout=StringIO())

        call = PhoneCall.objects.get(external_call_id="pbx-1")
        self.assertEqual(call.status, "answered")
        self.assertEqual(call.direction, "inbound")
        self.assertEqual(call.phone_from, "+7 (900) 000-00-00")
        self.assertEqual(call.phone_to, "+7 (495) 000-00-00")
        self.assertEqual(call.responsible_user_id, self.user.pk)

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
            novofon_employee_id="emp-2",
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
        self.assertEqual(call.lead_id, self.lead.pk)
        self.assertEqual(call.crm_user_id, self.user.pk)


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
    def test_sync_employees_returns_api_error_instead_of_http_500(self, list_employees_mock):
        list_employees_mock.side_effect = NovofonClientError("Метод get.employees недоступен для текущего токена.")

        response = self.client.post(reverse("telephony-novofon-sync-employees"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["ok"], False)
        self.assertIn("get.employees", response.data["error"])


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
