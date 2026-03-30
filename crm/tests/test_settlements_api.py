from decimal import Decimal
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
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
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))

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
        self.assertEqual(Decimal(summary_response.data["overview"]["expected_receivable"]), Decimal("60000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("0.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["balance"]), Decimal("0.00"))

    def test_realization_forms_actual_receivable_and_has_status(self):
        response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "realization",
                "number": "ACT-001",
                "document_date": "2026-03-30",
                "due_date": "2026-04-05",
                "currency": "RUB",
                "amount": "75000.00",
                "realization_status": "sent_to_client",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
        self.assertEqual(response.data["realization_status"], "sent_to_client")
        self.assertEqual(response.data["realization_status_label"], "Отправлен клиенту")

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["expected_receivable"]), Decimal("0.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("75000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["balance"]), Decimal("75000.00"))

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_upload_file_for_settlement_document(self):
        uploaded_file = SimpleUploadedFile("invoice-100000.pdf", b"%PDF-1.4", content_type="application/pdf")

        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                reverse("settlement-documents-list"),
                {
                    "client": self.company.pk,
                    "document_type": "invoice",
                    "number": "INV-FILE-001",
                    "document_date": "2026-03-30",
                    "currency": "RUB",
                    "amount": "100000.00",
                    "file": uploaded_file,
                    "original_name": "invoice-100000.pdf",
                },
                format="multipart",
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
            self.assertTrue(response.data["download_url"].endswith(f"/api/v1/settlements/documents/{response.data['id']}/download/"))
            self.assertIn(f"company_{self.company.pk}/settlements/", response.data["file_url"])
            self.assertEqual(response.data["original_name"], "invoice-100000.pdf")

            download_response = self.client.get(reverse("settlement-documents-download", kwargs={"pk": response.data["id"]}))
            self.assertEqual(download_response.status_code, status.HTTP_200_OK)
            self.assertEqual(download_response["Content-Disposition"], 'inline; filename="invoice-100000.pdf"')
