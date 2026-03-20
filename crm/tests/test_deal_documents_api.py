from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from crm.models import Client, Deal


class DealDocumentsApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff_deal_docs",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.company = Client.objects.create(name="Acme")
        self.deal = Deal.objects.create(title="Сделка для документов", client=self.company)

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
