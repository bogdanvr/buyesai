from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Lead


class LeadCompanyAutoCreateTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_leads",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

    def test_creates_client_and_links_lead_when_company_is_provided(self):
        response = self.client.post(
            reverse("leads-list"),
            {"title": "Lead A", "company": " Acme "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.get(pk=response.data["id"])
        self.assertEqual(lead.company, "Acme")
        self.assertIsNotNone(lead.client)
        self.assertEqual(lead.client.name, "Acme")

    def test_reuses_existing_client_case_insensitive(self):
        existing = Client.objects.create(name="Acme")

        response = self.client.post(
            reverse("leads-list"),
            {"title": "Lead B", "company": "acme"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.get(pk=response.data["id"])
        self.assertEqual(lead.client_id, existing.id)
        self.assertEqual(Client.objects.filter(name__iexact="acme").count(), 1)
