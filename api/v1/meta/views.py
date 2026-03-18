import logging
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import requests
from django.core.cache import cache
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.meta.serializers import (
    CommunicationChannelSerializer,
    DealStageSerializer,
    LeadSourceSerializer,
    LeadStatusSerializer,
)
from crm.models import CommunicationChannel, DealStage, LeadSource, LeadStatus

logger = logging.getLogger(__name__)
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


class CurrencyRatesAPIView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(_fetch_currency_rates())
