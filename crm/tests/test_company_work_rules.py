from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, CommunicationChannel, Contact


class CompanyWorkRulesTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_work_rules",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(name="Acme")
        self.other_company = Client.objects.create(name="Beta")
        self.contact = Contact.objects.create(
            client=self.company,
            first_name="Иван",
            last_name="Петров",
        )
        self.other_contact = Contact.objects.create(
            client=self.other_company,
            first_name="Петр",
            last_name="Иванов",
        )
        self.channel = CommunicationChannel.objects.create(name="Telegram", is_active=True)
        self.second_channel = CommunicationChannel.objects.create(name="Email", is_active=True)

    def test_company_work_rules_accept_contact_from_same_company_and_multiple_admin_channels(self):
        response = self.client.patch(
            reverse("clients-detail", kwargs={"pk": self.company.pk}),
            {
                "work_rules": {
                    "decision_maker_contact": self.contact.pk,
                    "communication_channels": [self.channel.pk, self.second_channel.pk],
                    "payment_terms": "Постоплата 30 дней",
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.company.refresh_from_db()
        self.assertEqual(self.company.work_rules.get("decision_maker_contact"), self.contact.pk)
        self.assertEqual(
            self.company.work_rules.get("communication_channels"),
            [self.channel.pk, self.second_channel.pk],
        )

    def test_company_work_rules_reject_contact_from_other_company(self):
        response = self.client.patch(
            reverse("clients-detail", kwargs={"pk": self.company.pk}),
            {
                "work_rules": {
                    "decision_maker_contact": self.other_contact.pk,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("work_rules", response.data)

    def test_company_work_rules_reject_decision_maker_on_create(self):
        response = self.client.post(
            reverse("clients-list"),
            {
                "name": "Gamma",
                "work_rules": {
                    "decision_maker_contact": self.contact.pk,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("work_rules", response.data)
