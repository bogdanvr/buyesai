import logging
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.meta.serializers import (
    AutomationRuleSerializer,
    CommunicationChannelSerializer,
    ContactRoleSerializer,
    ContactStatusSerializer,
    DealStageSerializer,
    LeadSourceSerializer,
    LeadStatusSerializer,
    NextStepTemplateSerializer,
    OutcomeCatalogSerializer,
    TaskCategorySerializer,
    TaskTypeSerializer,
    TouchResultSerializer,
    UserOptionSerializer,
)
from crm.models import (
    AutomationRule,
    CommunicationChannel,
    ContactRole,
    ContactStatus,
    DealStage,
    LeadSource,
    LeadStatus,
    NextStepTemplate,
    OutcomeCatalog,
    TaskCategory,
    TaskType,
    TouchResult,
)
from crm.models.activity import get_available_task_categories_for_user, get_available_task_types_for_user

logger = logging.getLogger(__name__)
User = get_user_model()
CBR_DAILY_XML_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
CBR_RATES_CACHE_KEY = "api:v1:meta:currency_rates_rub"
CBR_RATES_CACHE_TIMEOUT = 60 * 60 * 6
CBR_RATES_REQUEST_TIMEOUT = 3


def _parse_cbr_decimal(value: str) -> Decimal:
    normalized = str(value or "").strip().replace(",", ".")
    return Decimal(normalized)


def _fetch_currency_rates() -> dict:
    cached = cache.get(CBR_RATES_CACHE_KEY)
    if cached:
        return cached

    rates = {"RUB": 1.0}
    payload = {
        "base": "RUB",
        "rates": rates,
        "source_url": CBR_DAILY_XML_URL,
        "date": "",
    }

    try:
        response = requests.get(CBR_DAILY_XML_URL, timeout=CBR_RATES_REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        payload["date"] = root.attrib.get("Date", "")
        for element in root.findall("Valute"):
            code = str(element.findtext("CharCode") or "").strip().upper()
            if not code:
                continue
            nominal_raw = element.findtext("Nominal")
            value_raw = element.findtext("Value")
            try:
                nominal = _parse_cbr_decimal(nominal_raw)
                value = _parse_cbr_decimal(value_raw)
                if nominal <= 0:
                    continue
            except (InvalidOperation, TypeError):
                continue
            rates[code] = float(value / nominal)
    except requests.RequestException as error:
        logger.warning("Failed to fetch CBR currency rates: %s", error)
    except ElementTree.ParseError as error:
        logger.warning("Failed to parse CBR currency rates XML: %s", error)

    cache.set(CBR_RATES_CACHE_KEY, payload, CBR_RATES_CACHE_TIMEOUT)
    return payload


class LeadStatusListAPIView(ListAPIView):
    serializer_class = LeadStatusSerializer
    pagination_class = None

    def get_queryset(self):
        return LeadStatus.objects.filter(is_active=True).order_by("order", "name")


class DealStageListAPIView(ListAPIView):
    serializer_class = DealStageSerializer
    pagination_class = None

    def get_queryset(self):
        return DealStage.objects.filter(is_active=True).order_by("order", "name")


class LeadSourceListAPIView(ListCreateAPIView):
    serializer_class = LeadSourceSerializer
    pagination_class = None

    def get_queryset(self):
        return LeadSource.objects.filter(is_active=True).order_by("name")


class CommunicationChannelListAPIView(ListAPIView):
    serializer_class = CommunicationChannelSerializer
    pagination_class = None

    def get_queryset(self):
        return CommunicationChannel.objects.filter(is_active=True).order_by("name")


class ContactRoleListAPIView(ListAPIView):
    serializer_class = ContactRoleSerializer
    pagination_class = None

    def get_queryset(self):
        return ContactRole.objects.filter(is_active=True).order_by("name")


class ContactStatusListAPIView(ListAPIView):
    serializer_class = ContactStatusSerializer
    pagination_class = None

    def get_queryset(self):
        return ContactStatus.objects.filter(is_active=True).order_by("name")


class UserOptionListAPIView(ListAPIView):
    serializer_class = UserOptionSerializer
    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(is_active=True, is_staff=True).order_by("first_name", "last_name", "username")


class TaskTypeListAPIView(ListAPIView):
    serializer_class = TaskTypeSerializer
    pagination_class = None

    def get_queryset(self):
        return get_available_task_types_for_user(self.request.user).order_by("sort_order", "name")


class TaskCategoryListAPIView(ListAPIView):
    serializer_class = TaskCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return get_available_task_categories_for_user(self.request.user).order_by("sort_order", "name")


class TouchResultListAPIView(ListAPIView):
    serializer_class = TouchResultSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            TouchResult.objects
            .filter(is_active=True)
            .prefetch_related("lead_statuses", "deal_stages")
            .order_by("sort_order", "name")
        )


class OutcomeCatalogListAPIView(ListAPIView):
    serializer_class = OutcomeCatalogSerializer
    pagination_class = None

    def get_queryset(self):
        return OutcomeCatalog.objects.all().order_by("name")


class NextStepTemplateListAPIView(ListAPIView):
    serializer_class = NextStepTemplateSerializer
    pagination_class = None

    def get_queryset(self):
        return NextStepTemplate.objects.all().order_by("name")


class AutomationRuleListAPIView(ListAPIView):
    serializer_class = AutomationRuleSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            AutomationRule.objects
            .filter(is_active=True)
            .select_related("default_outcome", "next_step_template")
            .order_by("sort_order", "event_type")
        )


class CurrencyRatesAPIView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(_fetch_currency_rates())
