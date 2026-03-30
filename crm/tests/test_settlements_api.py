from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, SettlementDocument


class SettlementsApiTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_settlements",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(name="Acme", currency="RUB")

    def test_partial_allocation_keeps_document_balance_and_history(self):
        invoice_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "invoice",
                "number": "INV-001",
                "document_date": "2026-03-30",
                "due_date": "2026-04-10",
                "currency": "RUB",
                "amount": "100000.00",
            },
            format="json",
        )
        self.assertEqual(invoice_response.status_code, status.HTTP_201_CREATED)

        payment_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "incoming_payment",
                "number": "PAY-001",
                "document_date": "2026-03-31",
                "currency": "RUB",
                "amount": "40000.00",
            },
            format="json",
        )
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)

        allocation_response = self.client.post(
            reverse("settlement-allocations-list"),
            {
                "source_document": payment_response.data["id"],
                "target_document": invoice_response.data["id"],
                "amount": "40000.00",
                "allocated_at": "2026-03-31",
            },
            format="json",
        )
        self.assertEqual(allocation_response.status_code, status.HTTP_201_CREATED)

        invoice = SettlementDocument.objects.get(pk=invoice_response.data["id"])
        payment = SettlementDocument.objects.get(pk=payment_response.data["id"])
        self.assertEqual(invoice.open_amount, Decimal("60000.00"))
        self.assertEqual(payment.open_amount, Decimal("0.00"))

        detail_response = self.client.get(reverse("settlement-documents-detail", kwargs={"pk": invoice.pk}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(detail_response.data["open_amount"]), Decimal("60000.00"))
        self.assertEqual(len(detail_response.data["allocation_history"]), 1)
        self.assertEqual(detail_response.data["allocation_history"][0]["history_role"], "incoming")

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("60000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["balance"]), Decimal("60000.00"))
