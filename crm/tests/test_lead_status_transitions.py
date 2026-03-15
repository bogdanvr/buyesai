from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Lead, LeadStatus


class LeadStatusTransitionTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="lead_status_tester",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)

        self.statuses = {
            "new": self.ensure_status("new", "Новый", 10),
            "in_progress": self.ensure_status("in_progress", "В работе", 20),
            "attempting_contact": self.ensure_status("attempting_contact", "Попытка контакта", 30),
            "qualified": self.ensure_status("qualified", "Квалифицирован", 40),
            "unqualified": self.ensure_status("unqualified", "Неквалифицирован", 50, is_final=True),
            "lost": self.ensure_status("lost", "Потерян", 55, is_final=True),
            "spam": self.ensure_status("spam", "Спам", 56, is_final=True),
            "converted": self.ensure_status("converted", "Конвертирован", 60),
            "archived": self.ensure_status("archived", "В архиве", 70, is_final=True),
        }

    def ensure_status(self, code: str, name: str, order: int, is_final: bool = False) -> LeadStatus:
        status, _ = LeadStatus.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "order": order,
                "is_active": True,
                "is_final": is_final,
            },
        )
        return status

    def create_lead(self, status_code: str) -> Lead:
        return Lead.objects.create(
            title=f"Lead {status_code}",
            status=self.statuses[status_code],
        )

    def test_attempting_contact_can_move_to_qualified(self):
        lead = self.create_lead("attempting_contact")

        response = self.client.patch(
            reverse("leads-detail", kwargs={"pk": lead.pk}),
            {"status": self.statuses["qualified"].pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.status.code, "qualified")

    def test_unqualified_can_move_to_qualified(self):
        lead = self.create_lead("unqualified")

        response = self.client.patch(
            reverse("leads-detail", kwargs={"pk": lead.pk}),
            {"status": self.statuses["qualified"].pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.status.code, "qualified")

    def test_lost_can_move_to_any_status(self):
        target_codes = [
            "new",
            "in_progress",
            "attempting_contact",
            "qualified",
            "unqualified",
            "converted",
            "spam",
            "archived",
        ]

        for target_code in target_codes:
            lead = self.create_lead("lost")
            response = self.client.patch(
                reverse("leads-detail", kwargs={"pk": lead.pk}),
                {"status": self.statuses[target_code].pk},
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK, target_code)
            lead.refresh_from_db()
            self.assertEqual(lead.status.code, target_code)
