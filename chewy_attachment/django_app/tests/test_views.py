"""Unit tests for Django views"""

import io
import shutil
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from chewy_attachment.django_app.models import Attachment


TEST_STORAGE = Path(__file__).parent / "test_storage"


@override_settings(CHEWY_ATTACHMENT={"STORAGE_ROOT": TEST_STORAGE})
class TestAttachmentViews(TestCase):
    """Test cases for attachment API views"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        TEST_STORAGE.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if TEST_STORAGE.exists():
            shutil.rmtree(TEST_STORAGE)

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        User = get_user_model()

        self.user1 = User.objects.create_user(
            username="testuser1",
            password="testpass123",
        )
        self.user2 = User.objects.create_user(
            username="testuser2",
            password="testpass123",
        )

        self.test_file_content = b"Hello, this is test file content!"
        self.test_file_name = "test.txt"

    def tearDown(self):
        """Clean up after each test"""
        Attachment.objects.all().delete()

    def _create_test_file(self):
        """Create a test file for upload"""
        return io.BytesIO(self.test_file_content)

    def _upload_file(self, user, is_public=False):
        """Helper to upload a file"""
        self.client.force_authenticate(user=user)
        file = self._create_test_file()
        file.name = self.test_file_name

        response = self.client.post(
            "/files/",
            {"file": file, "is_public": is_public},
            format="multipart",
        )
        return response

    def test_upload_file_success(self):
        """Test successful file upload"""
        self.client.force_authenticate(user=self.user1)
        file = self._create_test_file()
        file.name = self.test_file_name

        response = self.client.post(
            "/files/",
            {"file": file, "is_public": False},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["original_name"], self.test_file_name)
        self.assertEqual(response.data["size"], len(self.test_file_content))
        self.assertEqual(response.data["owner_id"], str(self.user1.id))
        self.assertFalse(response.data["is_public"])

        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.first()
        self.assertEqual(attachment.original_name, self.test_file_name)

    def test_upload_file_unauthenticated_fails(self):
        """Test upload fails without authentication"""
        file = self._create_test_file()
        file.name = self.test_file_name

        response = self.client.post(
            "/files/",
            {"file": file},
            format="multipart",
        )

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_file_info_by_owner(self):
        """Test owner can get file info"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], file_id)

    def test_get_private_file_info_by_non_owner_fails(self):
        """Test non-owner cannot get private file info"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_public_file_info_anonymous(self):
        """Test anonymous user can get public file info"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], file_id)

    def test_delete_file_by_owner(self):
        """Test owner can delete file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_delete_file_by_non_owner_fails(self):
        """Test non-owner cannot delete file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_delete_public_file_by_non_owner_fails(self):
        """Test non-owner cannot delete even public file"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_file_by_owner(self):
        """Test owner can download file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/files/{file_id}/content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), self.test_file_content)

    def test_download_private_file_by_non_owner_fails(self):
        """Test non-owner cannot download private file"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f"/files/{file_id}/content/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_public_file_anonymous(self):
        """Test anonymous user can download public file"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/files/{file_id}/content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), self.test_file_content)

    def test_get_nonexistent_file_returns_404(self):
        """Test 404 for nonexistent file"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/files/00000000-0000-0000-0000-000000000000/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
