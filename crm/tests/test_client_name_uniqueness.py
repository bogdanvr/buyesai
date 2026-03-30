from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client


class ClientNameUniquenessTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_user",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

    def test_cannot_create_duplicate_company_name_case_insensitive(self):
        Client.objects.create(name="Acme")

        response = self.client.post(
            reverse("clients-list"),
            {"name": "  acme  "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_cannot_rename_company_to_existing_name(self):
        Client.objects.create(name="Acme")
        other = Client.objects.create(name="Beta")

        response = self.client.patch(
            reverse("clients-detail", kwargs={"pk": other.pk}),
            {"name": " ACME "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_can_save_phone_and_email(self):
        response = self.client.post(
            reverse("clients-list"),
            {"name": "Gamma", "phone": "+7 900 000-00-00", "email": "gamma@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Client.objects.get(pk=response.data["id"])
        self.assertEqual(company.phone, "+7 900 000-00-00")
        self.assertEqual(company.email, "gamma@example.com")
        self.assertEqual(company.company_type, Client.CompanyType.CLIENT)

    def test_can_save_company_type(self):
        response = self.client.post(
            reverse("clients-list"),
            {"name": "Own Company", "company_type": "own"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Client.objects.get(pk=response.data["id"])
        self.assertEqual(company.company_type, Client.CompanyType.OWN)

        detail_response = self.client.get(reverse("clients-detail", kwargs={"pk": company.pk}))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["company_type"], "own")

    def test_can_save_company_registry_and_bank_account_fields(self):
        response = self.client.post(
            reverse("clients-list"),
            {
                "name": "Delta",
                "currency": "RUB",
                "ogrn": "1205500003763",
                "kpp": "550301001",
                "settlement_account": "40702810900000000001",
                "correspondent_account": "30101810400000000225",
                "bik": "045004225",
                "bank_name": "АО Банк",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Client.objects.get(pk=response.data["id"])
        self.assertEqual(company.ogrn, "1205500003763")
        self.assertEqual(company.kpp, "550301001")
        self.assertEqual(company.settlement_account, "40702810900000000001")
        self.assertEqual(company.correspondent_account, "30101810400000000225")

        detail_response = self.client.get(reverse("clients-detail", kwargs={"pk": company.pk}))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["ogrn"], "1205500003763")
        self.assertEqual(detail_response.data["kpp"], "550301001")
        self.assertEqual(detail_response.data["settlement_account"], "40702810900000000001")
        self.assertEqual(detail_response.data["correspondent_account"], "30101810400000000225")
