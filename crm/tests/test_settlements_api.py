from decimal import Decimal
import shutil
import tempfile
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Contact, Deal, SettlementContract, SettlementDocument


class SettlementsApiTests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="staff_settlements",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=user)
        self.company = Client.objects.create(
            name="Acme",
            legal_name='ООО "Акме"',
            currency="RUB",
            address="г. Москва, ул. Тверская, д. 1",
            inn="7701234567",
            kpp="770101001",
            ogrn="1234567890123",
            settlement_account="40702810900000000001",
            correspondent_account="30101810400000000225",
            bik="044525225",
            bank_name="АО Банк",
            email="info@acme.example",
            phone="+79990000001",
        )
        self.contact = Contact.objects.create(
            client=self.company,
            first_name="Иван",
            last_name="Иванов",
            position="директор",
            phone="+79991112233",
            email="director@acme.example",
            is_primary=True,
        )
        self.company.work_rules = {"decision_maker_contact": self.contact.pk}
        self.company.save(update_fields=["work_rules"])
        self.executor_company = Client.objects.create(
            name="Buyes",
            legal_name='ООО "Байес"',
            company_type=Client.CompanyType.OWN,
            currency="RUB",
            address="г. Омск, ул. Ленина, д. 7",
            inn="5500000000",
            kpp="550001001",
            ogrn="1025500000000",
            settlement_account="40702810900000000077",
            correspondent_account="30101810600000000774",
            bik="045004774",
            bank_name="ПАО Банк",
            email="hello@buyes.ru",
            phone="+73812000000",
        )
        Contact.objects.create(
            client=self.executor_company,
            first_name="Петр",
            last_name="Петров",
            position="генеральный директор",
            phone="+73812000001",
            email="ceo@buyes.ru",
            is_primary=True,
        )
        self.deal = Deal.objects.create(title="Сделка Acme", client=self.company)
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))

    @staticmethod
    def _contract_document_xml(contract: SettlementContract) -> str:
        with contract.file.open("rb") as handle:
            with ZipFile(handle) as archive:
                return archive.read("word/document.xml").decode("utf-8")

    def test_old_advance_is_automatically_offset_when_act_is_created(self):
        payment_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "incoming_payment",
                "number": "PAY-ADV-001",
                "document_date": "2026-03-30",
                "currency": "RUB",
                "amount": "200000.00",
            },
            format="json",
        )
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED, payment_response.content.decode())
        self.assertFalse(payment_response.data["can_allocate_as_target"])

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["advances_received"]), Decimal("200000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("0.00"))

        realization_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "realization",
                "number": "ACT-001",
                "document_date": "2026-03-31",
                "due_date": "2026-04-10",
                "currency": "RUB",
                "amount": "120000.00",
                "deal": self.deal.pk,
                "realization_status": "created",
            },
            format="json",
        )
        self.assertEqual(realization_response.status_code, status.HTTP_201_CREATED, realization_response.content.decode())

        realization = SettlementDocument.objects.get(pk=realization_response.data["id"])
        payment = SettlementDocument.objects.get(pk=payment_response.data["id"])
        self.assertEqual(realization.open_amount, Decimal("0.00"))
        self.assertEqual(payment.open_amount, Decimal("80000.00"))

        detail_response = self.client.get(reverse("settlement-documents-detail", kwargs={"pk": realization.pk}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(detail_response.data["open_amount"]), Decimal("0.00"))
        self.assertEqual(len(detail_response.data["allocation_history"]), 1)
        self.assertEqual(detail_response.data["allocation_history"][0]["history_role"], "incoming")

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["advances_received"]), Decimal("80000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("0.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["balance"]), Decimal("-80000.00"))

    def test_incoming_payment_after_act_automatically_reduces_debt(self):
        realization_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "realization",
                "number": "ACT-001",
                "document_date": "2026-03-30",
                "due_date": "2026-04-05",
                "currency": "RUB",
                "amount": "120000.00",
                "deal": self.deal.pk,
                "realization_status": "sent_to_client",
            },
            format="json",
        )
        self.assertEqual(realization_response.status_code, status.HTTP_201_CREATED, realization_response.content.decode())

        payment_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "incoming_payment",
                "number": "PAY-001",
                "document_date": "2026-03-31",
                "currency": "RUB",
                "amount": "50000.00",
            },
            format="json",
        )
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED, payment_response.content.decode())

        realization = SettlementDocument.objects.get(pk=realization_response.data["id"])
        payment = SettlementDocument.objects.get(pk=payment_response.data["id"])
        self.assertEqual(realization.open_amount, Decimal("70000.00"))
        self.assertEqual(payment.open_amount, Decimal("0.00"))

        payment_detail = self.client.get(reverse("settlement-documents-detail", kwargs={"pk": payment.pk}))
        self.assertEqual(payment_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payment_detail.data["allocation_history"]), 1)
        self.assertEqual(payment_detail.data["allocation_history"][0]["history_role"], "outgoing")

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["expected_receivable"]), Decimal("0.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("70000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["advances_received"]), Decimal("0.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["balance"]), Decimal("70000.00"))

    def test_invoice_expected_receivable_is_reduced_by_realization_of_same_deal(self):
        invoice_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "deal": self.deal.pk,
                "document_type": "invoice",
                "document_date": "2026-03-30",
                "currency": "RUB",
                "amount": "100000.00",
                "number": "",
            },
            format="json",
        )
        self.assertEqual(invoice_response.status_code, status.HTTP_201_CREATED, invoice_response.content.decode())

        realization_response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "deal": self.deal.pk,
                "document_type": "realization",
                "document_date": "2026-03-31",
                "currency": "RUB",
                "amount": "40000.00",
                "number": "",
                "realization_status": "created",
            },
            format="json",
        )
        self.assertEqual(realization_response.status_code, status.HTTP_201_CREATED, realization_response.content.decode())

        summary_response = self.client.get(f"{reverse('settlement-summary')}?client={self.company.pk}")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_response.data["overview"]["expected_receivable"]), Decimal("60000.00"))
        self.assertEqual(Decimal(summary_response.data["overview"]["receivable"]), Decimal("40000.00"))

    def test_realization_requires_deal(self):
        response = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "realization",
                "document_date": "2026-03-30",
                "currency": "RUB",
                "amount": "1000.00",
                "realization_status": "created",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deal", response.data)

    def test_invoice_and_realization_get_separate_auto_numbers(self):
        first_invoice = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "invoice",
                "document_date": "2026-03-30",
                "currency": "RUB",
                "amount": "1000.00",
                "number": "",
            },
            format="json",
        )
        second_invoice = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "document_type": "invoice",
                "document_date": "2026-03-31",
                "currency": "RUB",
                "amount": "2000.00",
                "number": "",
            },
            format="json",
        )
        first_realization = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "deal": self.deal.pk,
                "document_type": "realization",
                "document_date": "2026-04-01",
                "currency": "RUB",
                "amount": "3000.00",
                "number": "",
                "realization_status": "created",
            },
            format="json",
        )
        second_realization = self.client.post(
            reverse("settlement-documents-list"),
            {
                "client": self.company.pk,
                "deal": self.deal.pk,
                "document_type": "realization",
                "document_date": "2026-04-02",
                "currency": "RUB",
                "amount": "4000.00",
                "number": "",
                "realization_status": "created",
            },
            format="json",
        )

        self.assertEqual(first_invoice.status_code, status.HTTP_201_CREATED, first_invoice.content.decode())
        self.assertEqual(second_invoice.status_code, status.HTTP_201_CREATED, second_invoice.content.decode())
        self.assertEqual(first_realization.status_code, status.HTTP_201_CREATED, first_realization.content.decode())
        self.assertEqual(second_realization.status_code, status.HTTP_201_CREATED, second_realization.content.decode())
        self.assertEqual(first_invoice.data["number"], "1235")
        self.assertEqual(second_invoice.data["number"], "1242")
        self.assertEqual(first_realization.data["number"], "1235")
        self.assertEqual(second_realization.data["number"], "1242")

    def test_legacy_advance_document_types_cannot_be_created(self):
        for document_type in ("advance", "advance_offset"):
            response = self.client.post(
                reverse("settlement-documents-list"),
                {
                    "client": self.company.pk,
                    "document_type": document_type,
                    "document_date": "2026-03-30",
                    "currency": "RUB",
                    "amount": "1000.00",
                    "flow_direction": "incoming",
                },
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_type", response.data)

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

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_generate_service_contract_from_template(self):
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                reverse("settlement-contracts-generate"),
                {
                    "client": self.company.pk,
                    "advance_percent": "50.00",
                    "hourly_rate": "2500.00",
                    "warranty_days": 45,
                    "claim_response_days": 7,
                    "termination_notice_days": 10,
                },
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
            contract = SettlementContract.objects.get(pk=response.data["id"])
            self.assertEqual(contract.number, "1")
            self.assertEqual(contract.hourly_rate, Decimal("2500.00"))
            self.assertEqual(contract.advance_percent, Decimal("50.00"))
            self.assertTrue(contract.original_name.endswith(".docx"))
            self.assertTrue(response.data["download_url"].endswith(f"/api/v1/settlements/contracts/{contract.pk}/download/"))
            self.assertIn(f"company_{self.company.pk}/contracts/", response.data["file_url"])

            xml = self._contract_document_xml(contract)
            self.assertIn("ДОГОВОР № 1", xml)
            self.assertIn('ООО "Акме"', xml)
            self.assertIn('ООО "Байес"', xml)
            self.assertIn("аванс в размере 50 % стоимости этапа", xml)
            self.assertIn("составляет 2500 рублей.", xml)
            self.assertIn("составляет 45 календарных дней", xml)
            self.assertIn("составляет 7 календарных дней с даты ее получения.", xml)
            self.assertIn("не менее чем за 10 календарных дней.", xml)

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_updating_generated_contract_regenerates_docx_and_keeps_number(self):
        with override_settings(MEDIA_ROOT=self.media_root):
            create_response = self.client.post(
                reverse("settlement-contracts-generate"),
                {
                    "client": self.company.pk,
                    "advance_percent": "20.00",
                    "hourly_rate": "1000.00",
                    "warranty_days": 31,
                    "claim_response_days": 5,
                    "termination_notice_days": 5,
                },
                format="json",
            )
            self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.content.decode())
            contract = SettlementContract.objects.get(pk=create_response.data["id"])
            original_number = contract.number

            update_response = self.client.patch(
                reverse("settlement-contracts-detail", kwargs={"pk": contract.pk}),
                {
                    "hourly_rate": "3000.00",
                    "advance_percent": "35.00",
                    "warranty_days": 60,
                },
                format="json",
            )

            self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.content.decode())
            contract.refresh_from_db()
            self.assertEqual(contract.number, original_number)
            xml = self._contract_document_xml(contract)
            self.assertIn(f"ДОГОВОР № {original_number}", xml)
            self.assertIn("аванс в размере 35 % стоимости этапа", xml)
            self.assertIn("составляет 3000 рублей.", xml)
            self.assertIn("составляет 60 календарных дней", xml)
