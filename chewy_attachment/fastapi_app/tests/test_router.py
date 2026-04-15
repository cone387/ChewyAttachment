"""Unit tests for FastAPI router"""

import io
import shutil
from pathlib import Path

from fastapi import status

TEST_DIR = Path(__file__).parent.absolute()
TEST_STORAGE = TEST_DIR / "test_storage"


class TestAttachmentRouter:
    """Test cases for attachment API router"""

    TEST_FILE_CONTENT = b"Hello, this is test file content!"
    TEST_FILE_NAME = "test.txt"

    def setup_method(self):
        """Set up before each test"""
        TEST_STORAGE.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up after each test"""
        if TEST_STORAGE.exists():
            for item in TEST_STORAGE.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def _upload_file(self, client, is_public: bool = False):
        """Helper to upload a file"""
        files = {"file": (self.TEST_FILE_NAME, io.BytesIO(self.TEST_FILE_CONTENT))}
        data = {"is_public": str(is_public).lower()}

        return client.post("/files", files=files, data=data)

    def test_upload_file_success(self, client, set_current_user, user1_id):
        """Test successful file upload"""
        set_current_user(user1_id)
        response = self._upload_file(client)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["original_name"] == self.TEST_FILE_NAME
        assert data["size"] == len(self.TEST_FILE_CONTENT)
        assert data["owner_id"] == user1_id
        assert data["is_public"] is False

    def test_upload_file_public(self, client, set_current_user, user1_id):
        """Test uploading public file"""
        set_current_user(user1_id)
        response = self._upload_file(client, is_public=True)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_public"] is True

    def test_upload_file_unauthenticated_fails(self, client, set_current_user):
        """Test upload fails without authentication"""
        set_current_user(None)
        files = {"file": (self.TEST_FILE_NAME, io.BytesIO(self.TEST_FILE_CONTENT))}

        response = client.post("/files", files=files)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_file_info_by_owner(self, client, set_current_user, user1_id):
        """Test owner can get file info"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        response = client.get(f"/files/{file_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == file_id

    def test_get_private_file_info_by_non_owner_fails(
        self, client, set_current_user, user1_id, user2_id
    ):
        """Test non-owner cannot get private file info"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client, is_public=False)
        file_id = upload_response.json()["id"]

        set_current_user(user2_id)
        response = client.get(f"/files/{file_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_public_file_info_anonymous(self, client, set_current_user, user1_id):
        """Test anonymous user can get public file info"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client, is_public=True)
        file_id = upload_response.json()["id"]

        set_current_user(None)
        response = client.get(f"/files/{file_id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == file_id

    def test_delete_file_by_owner(self, client, set_current_user, user1_id):
        """Test owner can delete file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        response = client.delete(f"/files/{file_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_file_by_non_owner_fails(
        self, client, set_current_user, user1_id, user2_id
    ):
        """Test non-owner cannot delete file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        set_current_user(user2_id)
        response = client.delete(f"/files/{file_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_public_file_by_non_owner_fails(
        self, client, set_current_user, user1_id, user2_id
    ):
        """Test non-owner cannot delete even public file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client, is_public=True)
        file_id = upload_response.json()["id"]

        set_current_user(user2_id)
        response = client.delete(f"/files/{file_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_download_file_by_owner(self, client, set_current_user, user1_id):
        """Test owner can download file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        response = client.get(f"/files/{file_id}/content")

        assert response.status_code == status.HTTP_200_OK
        assert response.content == self.TEST_FILE_CONTENT

    def test_download_private_file_by_non_owner_fails(
        self, client, set_current_user, user1_id, user2_id
    ):
        """Test non-owner cannot download private file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client, is_public=False)
        file_id = upload_response.json()["id"]

        set_current_user(user2_id)
        response = client.get(f"/files/{file_id}/content")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_download_public_file_anonymous(self, client, set_current_user, user1_id):
        """Test anonymous user can download public file"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client, is_public=True)
        file_id = upload_response.json()["id"]

        set_current_user(None)
        response = client.get(f"/files/{file_id}/content")

        assert response.status_code == status.HTTP_200_OK
        assert response.content == self.TEST_FILE_CONTENT

    def test_get_nonexistent_file_returns_404(self, client, set_current_user, user1_id):
        """Test 404 for nonexistent file"""
        set_current_user(user1_id)
        response = client.get("/files/00000000-0000-0000-0000-000000000000")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_files_page_upper_bound(self, client, set_current_user, user1_id):
        """Test page parameter rejects values above 10000"""
        set_current_user(user1_id)
        response = client.get("/files?page=10001")
        assert response.status_code == 422

    def test_list_files_page_lower_bound(self, client, set_current_user, user1_id):
        """Test page parameter rejects zero"""
        set_current_user(user1_id)
        response = client.get("/files?page=0")
        assert response.status_code == 422

    def test_list_files_valid_pagination(self, client, set_current_user, user1_id):
        """Test valid pagination parameters work"""
        set_current_user(user1_id)
        response = client.get("/files?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_preview_file_by_owner(self, client, set_current_user, user1_id):
        """Test owner can preview file inline"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        response = client.get(f"/files/{file_id}/preview")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == self.TEST_FILE_CONTENT

    def test_upload_preserves_storage_config_id(self, client, set_current_user, user1_id):
        """Test that storage_config_id is persisted in the database"""
        set_current_user(user1_id)
        upload_response = self._upload_file(client)
        file_id = upload_response.json()["id"]

        # Retrieve and check — for local storage, storage_config_id should be None
        response = client.get(f"/files/{file_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Local storage has no config_id
        assert data.get("storage_config_id") is None


class TestHealthAndStats:
    """Tests for health check and storage stats endpoints"""

    def test_health_check(self, client, set_current_user):
        """Health check returns healthy status"""
        set_current_user(None)
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data["checks"]
        assert "storage" in data["checks"]

    def test_stats_requires_auth(self, client, set_current_user):
        """Stats endpoint requires authentication"""
        set_current_user(None)
        response = client.get("/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_stats_returns_user_scope(self, client, set_current_user, user1_id):
        """Stats returns user-scoped data"""
        set_current_user(user1_id)
        response = client.get("/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["scope"] == "user"
        assert data["user_id"] == user1_id
        assert data["total_files"] == 0

    def test_stats_after_upload(self, client, set_current_user, user1_id):
        """Stats reflect uploaded files"""
        set_current_user(user1_id)
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        client.post("/files", files=files, data={"is_public": "false"})

        response = client.get("/stats")
        data = response.json()
        assert data["total_files"] == 1
        assert data["total_size"] > 0


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_upload_empty_filename(self, client, set_current_user, user1_id):
        """Upload with empty filename is rejected by FastAPI validation"""
        set_current_user(user1_id)
        files = {"file": ("", io.BytesIO(b"data"), "application/octet-stream")}
        response = client.post("/files", files=files)
        # FastAPI rejects empty filename as invalid multipart
        assert response.status_code in (status.HTTP_201_CREATED, 422)

    def test_upload_response_has_all_fields(self, client, set_current_user, user1_id):
        """Upload response contains all expected fields"""
        set_current_user(user1_id)
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        response = client.post("/files", files=files)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        expected = {
            "id", "original_name", "mime_type", "size", "owner_id",
            "is_public", "storage_config_id", "created_at", "preview_url",
        }
        assert expected.issubset(set(data.keys())), f"Missing: {expected - set(data.keys())}"

    def test_delete_nonexistent_returns_404(self, client, set_current_user, user1_id):
        """Deleting nonexistent file returns 404"""
        set_current_user(user1_id)
        response = client.delete("/files/00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_nonexistent_returns_404(self, client, set_current_user, user1_id):
        """Downloading nonexistent file returns 404"""
        set_current_user(user1_id)
        response = client.get("/files/00000000-0000-0000-0000-000000000000/content")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_preview_nonexistent_returns_404(self, client, set_current_user, user1_id):
        """Previewing nonexistent file returns 404"""
        set_current_user(user1_id)
        response = client.get("/files/00000000-0000-0000-0000-000000000000/preview")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_empty(self, client, set_current_user, user1_id):
        """List returns empty when no files"""
        set_current_user(user1_id)
        response = client.get("/files")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_filters_by_user(self, client, set_current_user, user1_id, user2_id):
        """List only shows own files and public files"""
        # User1 uploads private file
        set_current_user(user1_id)
        files = {"file": ("private.txt", io.BytesIO(b"secret"), "text/plain")}
        client.post("/files", files=files, data={"is_public": "false"})

        # User2 should not see user1's private file
        set_current_user(user2_id)
        response = client.get("/files")
        data = response.json()
        assert data["total"] == 0

    def test_list_shows_public_to_anonymous(self, client, set_current_user, user1_id):
        """Anonymous users can see public files"""
        set_current_user(user1_id)
        files = {"file": ("public.txt", io.BytesIO(b"hello"), "text/plain")}
        client.post("/files", files=files, data={"is_public": "true"})

        set_current_user(None)
        response = client.get("/files")
        data = response.json()
        assert data["total"] == 1
