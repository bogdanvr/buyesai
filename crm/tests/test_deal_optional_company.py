from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Deal


class DealOptionalCompanyTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_deals",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

    def test_can_create_deal_without_company(self):
        response = self.client.post(
            reverse("deals-list"),
            {"title": "Deal without company", "client": None},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deal = Deal.objects.get(pk=response.data["id"])
        self.assertIsNone(deal.client)

    def test_can_clear_company_on_deal_update(self):
        company = Client.objects.create(name="Acme")
        deal = Deal.objects.create(title="Deal with company", client=company)

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"client": None},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        deal.refresh_from_db()
        self.assertIsNone(deal.client)
