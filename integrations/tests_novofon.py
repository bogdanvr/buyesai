from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
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
    NovofonClient,
)
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

    def test_webhook_creates_phone_call_and_links_entities(self):
        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call = PhoneCall.objects.get(external_call_id="call-1")
        self.assertEqual(call.contact_id, self.contact.pk)
        self.assertEqual(call.company_id, self.company.pk)
        self.assertEqual(call.deal_id, self.deal.pk)
        self.assertEqual(call.responsible_user_id, self.user.pk)
        self.assertEqual(call.client_phone_normalized, "79000000000")

    def test_duplicate_webhook_is_marked_and_does_not_duplicate_call(self):
        self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-dup"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )
        response = self.client.post(
            reverse("integrations-novofon-webhook"),
            self._payload(event_id="event-dup"),
            format="json",
            HTTP_X_WEBHOOK_SECRET="secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PhoneCall.objects.filter(external_call_id="call-1").count(), 1)
        statuses = list(TelephonyEventLog.objects.order_by("id").values_list("status", flat=True))
        self.assertEqual(statuses, [TelephonyEventStatus.PROCESSED, TelephonyEventStatus.IGNORED_DUPLICATE])


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
