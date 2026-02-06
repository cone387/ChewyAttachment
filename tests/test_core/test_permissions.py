"""Tests for permission checking"""

import pytest
from datetime import datetime

from chewy_attachment.core.permissions import PermissionChecker
from chewy_attachment.core.schemas import FileMetadata, UserContext


@pytest.fixture
def public_file():
    """Create a public file metadata"""
    return FileMetadata(
        id="file-001",
        original_name="public.jpg",
        storage_path="2026/01/01/public.jpg",
        mime_type="image/jpeg",
        size=1024,
        owner_id="user-001",
        is_public=True,
        created_at=datetime.now(),
    )


@pytest.fixture
def private_file():
    """Create a private file metadata"""
    return FileMetadata(
        id="file-002",
        original_name="private.pdf",
        storage_path="2026/01/01/private.pdf",
        mime_type="application/pdf",
        size=2048,
        owner_id="user-001",
        is_public=False,
        created_at=datetime.now(),
    )


@pytest.fixture
def owner_user():
    """Create owner user context"""
    return UserContext.authenticated("user-001")


@pytest.fixture
def other_user():
    """Create another user context"""
    return UserContext.authenticated("user-002")


@pytest.fixture
def anonymous_user():
    """Create anonymous user context"""
    return UserContext.anonymous()


class TestPermissionChecker:
    """Tests for PermissionChecker"""

    # View permission tests
    def test_anonymous_can_view_public_file(self, public_file, anonymous_user):
        """Anonymous users can view public files"""
        assert PermissionChecker.can_view(public_file, anonymous_user) is True

    def test_anonymous_cannot_view_private_file(self, private_file, anonymous_user):
        """Anonymous users cannot view private files"""
        assert PermissionChecker.can_view(private_file, anonymous_user) is False

    def test_owner_can_view_private_file(self, private_file, owner_user):
        """Owners can view their private files"""
        assert PermissionChecker.can_view(private_file, owner_user) is True

    def test_other_user_cannot_view_private_file(self, private_file, other_user):
        """Other users cannot view private files"""
        assert PermissionChecker.can_view(private_file, other_user) is False

    def test_other_user_can_view_public_file(self, public_file, other_user):
        """Other users can view public files"""
        assert PermissionChecker.can_view(public_file, other_user) is True

    # Download permission tests (same as view)
    def test_download_permission_same_as_view(self, public_file, private_file, anonymous_user):
        """Download permission follows same rules as view"""
        assert PermissionChecker.can_download(public_file, anonymous_user) is True
        assert PermissionChecker.can_download(private_file, anonymous_user) is False

    # Delete permission tests
    def test_owner_can_delete_own_file(self, public_file, owner_user):
        """Owners can delete their files"""
        assert PermissionChecker.can_delete(public_file, owner_user) is True

    def test_other_user_cannot_delete_file(self, public_file, other_user):
        """Other users cannot delete files they don't own"""
        assert PermissionChecker.can_delete(public_file, other_user) is False

    def test_anonymous_cannot_delete_file(self, public_file, anonymous_user):
        """Anonymous users cannot delete files"""
        assert PermissionChecker.can_delete(public_file, anonymous_user) is False

    # Check permission methods
    def test_check_view_permission_returns_none_when_allowed(self, public_file, anonymous_user):
        """check_view_permission returns None when allowed"""
        result = PermissionChecker.check_view_permission(public_file, anonymous_user)
        assert result is None

    def test_check_view_permission_returns_message_when_denied(self, private_file, anonymous_user):
        """check_view_permission returns error message when denied"""
        result = PermissionChecker.check_view_permission(private_file, anonymous_user)
        assert result is not None
        assert "permission" in result.lower()

    def test_check_delete_permission_returns_message_when_denied(self, public_file, other_user):
        """check_delete_permission returns error message when denied"""
        result = PermissionChecker.check_delete_permission(public_file, other_user)
        assert result is not None
        assert "owner" in result.lower()


class TestUserContext:
    """Tests for UserContext"""

    def test_anonymous_user_is_not_authenticated(self):
        """Anonymous user is not authenticated"""
        user = UserContext.anonymous()
        assert user.is_authenticated is False
        assert user.user_id is None

    def test_authenticated_user_has_user_id(self):
        """Authenticated user has user_id"""
        user = UserContext.authenticated("user-123")
        assert user.is_authenticated is True
        assert user.user_id == "user-123"
