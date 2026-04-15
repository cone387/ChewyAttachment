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
            "/api/attachments/files/",
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
            "/api/attachments/files/",
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
            "/api/attachments/files/",
            {"file": file},
            format="multipart",
        )

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_file_info_by_owner(self):
        """Test owner can get file info"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/attachments/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], file_id)

    def test_get_private_file_info_by_non_owner_fails(self):
        """Test non-owner cannot get private file info"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f"/api/attachments/files/{file_id}/")

        # Private files return 404 to non-owners to avoid leaking file existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_public_file_info_anonymous(self):
        """Test anonymous user can get public file info"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/attachments/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], file_id)

    def test_delete_file_by_owner(self):
        """Test owner can delete file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f"/api/attachments/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_delete_file_by_non_owner_fails(self):
        """Test non-owner cannot delete file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/api/attachments/files/{file_id}/")

        # Private files return 404 to non-owners to avoid leaking file existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_delete_public_file_by_non_owner_fails(self):
        """Test non-owner cannot delete even public file"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/api/attachments/files/{file_id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_file_by_owner(self):
        """Test owner can download file"""
        upload_response = self._upload_file(self.user1)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/attachments/files/{file_id}/content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), self.test_file_content)

    def test_download_private_file_by_non_owner_fails(self):
        """Test non-owner cannot download private file"""
        upload_response = self._upload_file(self.user1, is_public=False)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f"/api/attachments/files/{file_id}/content/")

        # Private files return 404 to non-owners to avoid leaking file existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_public_file_anonymous(self):
        """Test anonymous user can download public file"""
        upload_response = self._upload_file(self.user1, is_public=True)
        file_id = upload_response.data["id"]

        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/attachments/files/{file_id}/content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), self.test_file_content)

    def test_get_nonexistent_file_returns_404(self):
        """Test 404 for nonexistent file"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/attachments/files/00000000-0000-0000-0000-000000000000/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(CHEWY_ATTACHMENT={"STORAGE_ROOT": TEST_STORAGE})
class TestHealthCheckView(TestCase):
    """Tests for /health/ endpoint"""

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
        self.client = APIClient()

    def test_health_check_returns_200(self):
        """Health check returns 200 when everything is healthy"""
        response = self.client.get("/api/attachments/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("version", data)
        self.assertIn("database", data["checks"])
        self.assertIn("storage", data["checks"])

    def test_health_check_no_auth_required(self):
        """Health check works without authentication"""
        response = self.client.get("/api/attachments/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(CHEWY_ATTACHMENT={"STORAGE_ROOT": TEST_STORAGE})
class TestStorageStatsView(TestCase):
    """Tests for /stats/ endpoint"""

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
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="statsuser", password="pass123")

    def test_stats_requires_auth(self):
        """Stats endpoint requires authentication"""
        response = self.client.get("/api/attachments/stats/")
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_stats_returns_user_scope(self):
        """Stats returns user-scoped data for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/attachments/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["scope"], "user")
        self.assertEqual(data["user_id"], str(self.user.id))
        self.assertEqual(data["total_files"], 0)
        self.assertIn("by_mime_type", data)
        self.assertIn("by_storage", data)

    def test_stats_after_upload(self):
        """Stats reflect uploaded files"""
        self.client.force_authenticate(user=self.user)
        f = io.BytesIO(b"hello world")
        f.name = "test.txt"
        self.client.post("/api/attachments/files/", {"file": f}, format="multipart")

        response = self.client.get("/api/attachments/stats/")
        data = response.json()
        self.assertEqual(data["total_files"], 1)
        self.assertGreater(data["total_size"], 0)


@override_settings(CHEWY_ATTACHMENT={"STORAGE_ROOT": TEST_STORAGE})
class TestPreviewAndListViews(TestCase):
    """Tests for preview and list endpoints"""

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
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="previewuser", password="pass123")
        self.content = b"preview test content"

    def tearDown(self):
        Attachment.objects.all().delete()

    def _upload(self, is_public=False):
        self.client.force_authenticate(user=self.user)
        f = io.BytesIO(self.content)
        f.name = "test.txt"
        return self.client.post(
            "/api/attachments/files/",
            {"file": f, "is_public": is_public},
            format="multipart",
        )

    def test_preview_by_owner(self):
        """Owner can preview file inline"""
        resp = self._upload()
        file_id = resp.data["id"]
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/attachments/files/{file_id}/preview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), self.content)

    def test_preview_private_by_anonymous_fails(self):
        """Anonymous cannot preview private file"""
        resp = self._upload(is_public=False)
        file_id = resp.data["id"]
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/attachments/files/{file_id}/preview/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_pagination(self):
        """List endpoint supports pagination"""
        for _ in range(3):
            self._upload(is_public=True)
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/attachments/files/?page_size=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 3)

    def test_upload_response_has_all_fields(self):
        """Upload response contains all expected fields"""
        resp = self._upload()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        expected_fields = {
            "id", "original_name", "mime_type", "size", "owner_id",
            "is_public", "storage_config_id", "created_at",
            "preview_url", "download_url", "file_url",
        }
        self.assertTrue(expected_fields.issubset(set(resp.data.keys())), 
                        f"Missing fields: {expected_fields - set(resp.data.keys())}")

    def test_delete_removes_physical_file(self):
        """Deleting attachment also removes the physical file"""
        resp = self._upload()
        file_id = resp.data["id"]
        attachment = Attachment.objects.get(pk=file_id)
        storage_path = attachment.storage_path
        full_path = TEST_STORAGE / storage_path
        self.assertTrue(full_path.exists())

        self.client.force_authenticate(user=self.user)
        self.client.delete(f"/api/attachments/files/{file_id}/")
        self.assertFalse(full_path.exists())
        self.assertEqual(Attachment.objects.count(), 0)
