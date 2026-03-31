from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from zipfile import ZipFile

from crm.models import Client, ClientDocument, Deal, DealDocument, SettlementContract, SettlementDocument


class DealDocumentsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_deal_docs",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(
            name="Acme",
            legal_name='ООО "Акме"',
            inn="5501000000",
            kpp="550101001",
            address="г. Омск, ул. Ленина, д. 1",
            bank_name="АО Альфа-Банк",
            bik="044525593",
            settlement_account="40702810000000000001",
            correspondent_account="30101810200000000593",
            currency="KZT",
        )
        self.own_company = Client.objects.create(
            name="Buseys",
            legal_name='ООО "Buseys"',
            company_type=Client.CompanyType.OWN,
            inn="5501999999",
            kpp="550101001",
            ogrn="1205500003763",
            address="г. Омск, ул. Гагарина, д. 3",
            bank_name="АО Альфа-Банк",
            bik="044525593",
            settlement_account="40702810000000000009",
            correspondent_account="30101810200000000593",
            currency="KZT",
        )
        self.deal = Deal.objects.create(title="Сделка для документов", client=self.company, amount="77000.00", currency="RUB")
        self.contract_old = SettlementContract.objects.create(
            client=self.company,
            title="Договор 2025",
            number="2025-01",
            currency="KZT",
            hourly_rate="800.00",
            is_active=True,
        )
        self.contract_latest = SettlementContract.objects.create(
            client=self.company,
            title="Договор 2026",
            number="2026-02",
            currency="KZT",
            hourly_rate="1000.00",
            is_active=True,
        )

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_upload_document_with_long_filename_after_company_deal_prefix(self):
        long_filename = f'{"a" * 140}.txt'
        uploaded_file = SimpleUploadedFile(long_filename, b"hello", content_type="text/plain")

        response = self.client.post(
            reverse("deal-documents-list"),
            {
                "deal": self.deal.pk,
                "file": uploaded_file,
                "original_name": long_filename,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
        self.assertEqual(response.data["deal"], self.deal.pk)
        self.assertIn(f"company_{self.company.pk}/deal_{self.deal.pk}/", response.data["file_url"])

    def test_deal_document_writes_event_to_deal_and_company(self):
        document = DealDocument.objects.create(
            deal=self.deal,
            file=SimpleUploadedFile("proposal.pdf", b"pdf", content_type="application/pdf"),
            original_name="proposal.pdf",
            uploaded_by=self.user,
        )

        self.deal.refresh_from_db()
        self.company.refresh_from_db()

        expected_url = reverse("deal-documents-download", kwargs={"pk": document.pk})
        self.assertIn("event_type: document", self.deal.events)
        self.assertIn("document_name: proposal.pdf", self.deal.events)
        self.assertIn(f"document_url: {expected_url}", self.deal.events)
        self.assertIn("event_type: document", self.company.events)
        self.assertIn("document_name: proposal.pdf", self.company.events)

    def test_company_document_writes_event_to_company(self):
        document = ClientDocument.objects.create(
            client=self.company,
            file=SimpleUploadedFile("brief.docx", b"doc", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            original_name="brief.docx",
            uploaded_by=self.user,
        )

        self.company.refresh_from_db()

        expected_url = reverse("client-documents-download", kwargs={"pk": document.pk})
        self.assertIn("event_type: document", self.company.events)
        self.assertIn("document_name: brief.docx", self.company.events)
        self.assertIn(f"document_url: {expected_url}", self.company.events)

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_generate_act_document_for_deal(self):
        response = self.client.post(
            reverse("deal-documents-generate-act"),
            {
                "deal": self.deal.pk,
                "executor_company": self.own_company.pk,
                "items": [
                    {
                        "description": "Письменный перевод и оформление текста",
                        "quantity": "12.00",
                        "unit": "час",
                        "price": "3500.00",
                    },
                    {
                        "description": "Устный последовательный перевод",
                        "quantity": "2.00",
                        "unit": "час",
                        "price": "5000.00",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
        self.assertEqual(response.data["deal"], self.deal.pk)
        self.assertTrue(response.data["original_name"].endswith(".docx"))

        realization = SettlementDocument.objects.get(deal=self.deal, document_type=SettlementDocument.DocumentType.REALIZATION)
        self.assertEqual(str(realization.amount), "52000.00")
        self.assertEqual(realization.number, "1235")
        self.assertEqual(realization.currency, "KZT")
        self.assertEqual(realization.contract_id, self.contract_latest.pk)
        self.assertTrue(bool(realization.file))

        generated_document = DealDocument.objects.get(pk=response.data["id"])
        self.assertEqual(generated_document.uploaded_by, self.user)
        self.assertIn(f"company_{self.company.pk}/deal_{self.deal.pk}/", generated_document.file.name)
        self.assertEqual(realization.original_name, generated_document.original_name)
        self.assertEqual(generated_document.settlement_document_id, realization.pk)
        self.assertEqual(realization.generator_payload.get("executor_company_id"), self.own_company.pk)
        self.assertEqual(realization.generator_payload.get("contract_id"), self.contract_latest.pk)
        self.assertEqual(len(realization.generator_payload.get("items", [])), 2)

        with generated_document.file.open("rb") as file_handle:
            archive = ZipFile(file_handle)
            self.assertIn("word/document.xml", archive.namelist())
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("Акт об оказании услуг", document_xml)
        self.assertIn('ООО "Buseys"', document_xml)
        self.assertIn("Письменный перевод и оформление текста", document_xml)
        self.assertIn("Устный последовательный перевод", document_xml)
        self.assertIn("52000,00", document_xml.replace(" ", ""))
        self.assertIn("KZT", document_xml)

        download_response = self.client.get(reverse("deal-documents-download", kwargs={"pk": generated_document.pk}))
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertIn("filename*=utf-8''", download_response["Content-Disposition"])

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_generate_invoice_document_for_deal(self):
        response = self.client.post(
            reverse("deal-documents-generate-invoice"),
            {
                "deal": self.deal.pk,
                "executor_company": self.own_company.pk,
                "items": [
                    {
                        "description": "Переводческое сопровождение",
                        "quantity": "3.00",
                        "unit": "час",
                        "price": "12000.00",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content.decode())
        invoice = SettlementDocument.objects.get(deal=self.deal, document_type=SettlementDocument.DocumentType.INVOICE)
        self.assertEqual(str(invoice.amount), "36000.00")
        self.assertEqual(invoice.number, "1235")
        self.assertEqual(invoice.title, "Счет на оплату")
        self.assertEqual(invoice.currency, "KZT")
        self.assertEqual(invoice.contract_id, self.contract_latest.pk)
        self.assertTrue(bool(invoice.file))
        self.assertEqual(invoice.generator_payload.get("executor_company_id"), self.own_company.pk)
        self.assertEqual(invoice.generator_payload.get("contract_id"), self.contract_latest.pk)
        self.assertEqual(len(invoice.generator_payload.get("items", [])), 1)

        generated_document = DealDocument.objects.get(pk=response.data["id"])
        self.assertEqual(invoice.original_name, generated_document.original_name)
        self.assertIn("Счет", generated_document.original_name)
        self.assertEqual(generated_document.settlement_document_id, invoice.pk)
        self.assertEqual(response.data["generated_document_type"], "invoice")
        self.assertTrue(response.data["editable_generated_document"])
        self.assertEqual(response.data["settlement_document_id"], invoice.pk)
        self.assertEqual(response.data["generator_payload"]["executor_company_id"], self.own_company.pk)
        self.assertEqual(response.data["generator_payload"]["contract_id"], self.contract_latest.pk)

        with generated_document.file.open("rb") as file_handle:
            archive = ZipFile(file_handle)
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("Счет на оплату", document_xml)
        self.assertIn("Банк получателя", document_xml)
        self.assertIn("БИК", document_xml)
        self.assertIn("к/с №", document_xml)
        self.assertIn("р/с №", document_xml)
        self.assertIn("АО Альфа-Банк", document_xml)
        self.assertIn("40702810000000000009", document_xml)
        self.assertIn("30101810200000000593", document_xml)
        self.assertIn("Поставщик", document_xml)
        self.assertIn("Покупатель", document_xml)
        self.assertIn("Всего к оплате:", document_xml)
        self.assertIn("Переводческое сопровождение", document_xml)
        self.assertIn("36000,00", document_xml.replace(" ", ""))
        self.assertIn('<w:jc w:val="right"/>', document_xml)
        self.assertIn('<w:tblInd w:w="26" w:type="dxa"/>', document_xml)
        self.assertIn('<w:gridCol w:w="4364"/>', document_xml)
        self.assertIn('<w:gridCol w:w="2788"/>', document_xml)
        self.assertIn('<w:gridCol w:w="1199"/>', document_xml)
        self.assertIn('<w:gridCol w:w="1730"/>', document_xml)
        self.assertIn('<w:vAlign w:val="center"/>', document_xml)
        self.assertIn('<w:tblLayout w:type="fixed"/>', document_xml)

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def test_can_regenerate_invoice_document_preserving_number_and_writing_deal_event(self):
        create_response = self.client.post(
            reverse("deal-documents-generate-invoice"),
            {
                "deal": self.deal.pk,
                "executor_company": self.own_company.pk,
                "items": [
                    {
                        "description": "Первоначальная услуга",
                        "quantity": "2.00",
                        "unit": "час",
                        "price": "10000.00",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.content.decode())

        generated_document = DealDocument.objects.get(pk=create_response.data["id"])
        invoice = SettlementDocument.objects.get(pk=generated_document.settlement_document_id)
        original_number = invoice.number
        replacement_contract = SettlementContract.objects.create(
            client=self.company,
            title="Договор 2027",
            number="2027-03",
            currency="KZT",
            hourly_rate="1500.00",
            is_active=True,
        )

        update_response = self.client.post(
            reverse("deal-documents-regenerate", kwargs={"pk": generated_document.pk}),
            {
                "executor_company": self.own_company.pk,
                "contract": replacement_contract.pk,
                "items": [
                    {
                        "description": "Обновленная услуга",
                        "quantity": "3.00",
                        "unit": "час",
                        "price": "15000.00",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.content.decode())
        generated_document.refresh_from_db()
        invoice.refresh_from_db()
        self.deal.refresh_from_db()

        self.assertEqual(invoice.number, original_number)
        self.assertEqual(str(invoice.amount), "45000.00")
        self.assertEqual(invoice.contract_id, replacement_contract.pk)
        self.assertEqual(generated_document.settlement_document_id, invoice.pk)
        self.assertEqual(update_response.data["id"], generated_document.pk)
        self.assertEqual(update_response.data["settlement_document_id"], invoice.pk)
        self.assertTrue(update_response.data["editable_generated_document"])
        self.assertEqual(update_response.data["generated_document_type"], "invoice")
        self.assertEqual(update_response.data["generator_payload"]["executor_company_id"], self.own_company.pk)
        self.assertEqual(update_response.data["generator_payload"]["contract_id"], replacement_contract.pk)
        self.assertEqual(update_response.data["generator_payload"]["number"], original_number)
        self.assertEqual(update_response.data["generator_payload"]["items"][0]["description"], "Обновленная услуга")
        self.assertIn("Редактирование счета", self.deal.events)
        self.assertIn("event_type: document_edited", self.deal.events)

        with generated_document.file.open("rb") as file_handle:
            archive = ZipFile(file_handle)
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("Обновленная услуга", document_xml)
        self.assertIn("45000,00", document_xml.replace(" ", ""))
