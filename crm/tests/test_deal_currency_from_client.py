from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Deal, DealStage, TrafficSource


class DealCurrencyFromClientTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_deal_currency",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(name="Acme USD", currency="USD")
        self.source = TrafficSource.objects.create(name="Сайт", code="site")
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )

    def test_returns_company_currency_even_if_deal_stores_rub(self):
        deal = Deal.objects.create(
            title="USD deal",
            source=self.source,
            client=self.company,
            stage=self.stage,
            amount=100,
            currency="RUB",
        )

        response = self.client.get(reverse("deals-detail", kwargs={"pk": deal.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["currency"], "USD")
