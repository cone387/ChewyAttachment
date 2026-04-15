"""Tests for Django serializers — file validation"""

import io
import shutil
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from chewy_attachment.django_app.serializers import AttachmentUploadSerializer


TEST_STORAGE = Path(__file__).parent / "test_storage_ser"


@override_settings(CHEWY_ATTACHMENT={"STORAGE_ROOT": TEST_STORAGE})
class TestAttachmentUploadSerializer(TestCase):
    """Tests for AttachmentUploadSerializer validation"""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if TEST_STORAGE.exists():
            shutil.rmtree(TEST_STORAGE)

    def test_valid_file(self):
        """Normal file passes validation"""
        f = SimpleUploadedFile("test.txt", b"hello world", content_type="text/plain")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertTrue(serializer.is_valid())

    @override_settings(CHEWY_ATTACHMENT={
        "STORAGE_ROOT": TEST_STORAGE,
        "MAX_FILE_SIZE": 10,
    })
    def test_file_size_limit(self):
        """File exceeding MAX_FILE_SIZE is rejected"""
        f = SimpleUploadedFile("big.txt", b"x" * 100, content_type="text/plain")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    @override_settings(CHEWY_ATTACHMENT={
        "STORAGE_ROOT": TEST_STORAGE,
        "ALLOWED_EXTENSIONS": [".txt", ".pdf"],
    })
    def test_allowed_extensions_pass(self):
        """File with allowed extension passes"""
        f = SimpleUploadedFile("doc.txt", b"hello", content_type="text/plain")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertTrue(serializer.is_valid())

    @override_settings(CHEWY_ATTACHMENT={
        "STORAGE_ROOT": TEST_STORAGE,
        "ALLOWED_EXTENSIONS": [".txt", ".pdf"],
    })
    def test_disallowed_extension_rejected(self):
        """File with disallowed extension is rejected"""
        f = SimpleUploadedFile("hack.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    @override_settings(CHEWY_ATTACHMENT={
        "STORAGE_ROOT": TEST_STORAGE,
        "VALIDATE_MIME_CONTENT": True,
    })
    def test_mime_content_validation_safe_file_passes(self):
        """Normal text file passes MIME content validation"""
        f = SimpleUploadedFile("readme.txt", b"Just some text content", content_type="text/plain")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertTrue(serializer.is_valid())

    @override_settings(CHEWY_ATTACHMENT={
        "STORAGE_ROOT": TEST_STORAGE,
        "VALIDATE_MIME_CONTENT": False,
    })
    def test_mime_validation_disabled_by_default(self):
        """MIME content validation is off by default — any content passes"""
        # ELF header disguised as .jpg — should pass when validation is disabled
        elf_header = b"\x7fELF" + b"\x00" * 100
        f = SimpleUploadedFile("photo.jpg", elf_header, content_type="image/jpeg")
        serializer = AttachmentUploadSerializer(data={"file": f})
        self.assertTrue(serializer.is_valid())
