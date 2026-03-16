from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase


class CurrencyRatesAPITests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("api.v1.meta.views.requests.get")
    def test_returns_cbr_currency_rates_in_rub_per_unit(self, requests_get_mock):
        response_mock = Mock()
        response_mock.content = b"""
            <ValCurs Date="16.03.2026" name="Foreign Currency Market">
              <Valute ID="R01235">
                <NumCode>840</NumCode>
                <CharCode>USD</CharCode>
                <Nominal>1</Nominal>
                <Name>US Dollar</Name>
                <Value>86,5000</Value>
              </Valute>
              <Valute ID="R01239">
                <NumCode>978</NumCode>
                <CharCode>EUR</CharCode>
                <Nominal>1</Nominal>
                <Name>Euro</Name>
                <Value>94,2500</Value>
              </Valute>
              <Valute ID="R01335">
                <NumCode>398</NumCode>
                <CharCode>KZT</CharCode>
                <Nominal>100</Nominal>
                <Name>Kazakhstani tenge</Name>
                <Value>17,3000</Value>
              </Valute>
            </ValCurs>
        """
        response_mock.raise_for_status.return_value = None
        requests_get_mock.return_value = response_mock

        response = self.client.get("/api/v1/meta/currency-rates/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["base"], "RUB")
        self.assertEqual(payload["date"], "16.03.2026")
        self.assertEqual(payload["source_url"], "https://www.cbr.ru/scripts/XML_daily.asp")
        self.assertEqual(payload["rates"]["RUB"], 1.0)
        self.assertEqual(payload["rates"]["USD"], 86.5)
        self.assertEqual(payload["rates"]["EUR"], 94.25)
        self.assertEqual(payload["rates"]["KZT"], 0.173)
