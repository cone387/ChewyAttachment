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
