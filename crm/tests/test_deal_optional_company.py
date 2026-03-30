from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Contact, Deal, DealStage, Lead, LeadSource


class DealOptionalCompanyTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_deals",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.source = LeadSource.objects.create(name="Сайт", code="site")
        self.stage = DealStage.objects.create(
            name="В работе",
            code="in_progress",
            order=10,
            is_active=True,
            is_final=False,
        )

    def test_can_create_deal_without_company(self):
        response = self.client.post(
            reverse("deals-list"),
            {"title": "Deal without company", "client": None, "source": self.source.pk, "stage": self.stage.pk, "has_pending_task": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        deal = Deal.objects.get(pk=response.data["id"])
        self.assertIsNone(deal.client)

    def test_can_clear_company_on_deal_update(self):
        company = Client.objects.create(name="Acme")
        deal = Deal.objects.create(title="Deal with company", client=company, source=self.source, stage=self.stage)

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"client": None, "has_pending_task": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        deal.refresh_from_db()
        self.assertIsNone(deal.client)

    def test_can_filter_deals_by_company(self):
        company = Client.objects.create(name="Acme")
        other_company = Client.objects.create(name="Beta")
        target_deal = Deal.objects.create(title="Deal for Acme", client=company)
        Deal.objects.create(title="Deal for Beta", client=other_company)

        response = self.client.get(reverse("deals-list"), {"client": company.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(result_ids, {target_deal.pk})

    def test_first_company_bind_on_deal_creates_company_contact_from_lead(self):
        company = Client.objects.create(name="Acme")
        lead = Lead.objects.create(
            title="Lead without company",
            company="",
            name="Иван Иванов",
            email="ivan@acme.test",
            phone="+7 900 123-45-67",
        )
        deal = Deal.objects.create(
            title="Deal from lead",
            client=None,
            lead=lead,
            source=self.source,
            stage=self.stage,
        )

        response = self.client.patch(
            reverse("deals-detail", kwargs={"pk": deal.pk}),
            {"client": company.pk, "has_pending_task": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.email, "ivan@acme.test")

        contact = Contact.objects.filter(client=company).get()
        self.assertEqual(contact.first_name, "Иван")
        self.assertEqual(contact.last_name, "Иванов")
        self.assertEqual(contact.email, "ivan@acme.test")
        self.assertEqual(contact.phone, "+7 900 123-45-67")
