"""Tests for StorageManager"""

import shutil
from pathlib import Path

import pytest

from chewy_attachment.core.exceptions import StorageException
from chewy_attachment.core.storage import (
    FileStorageEngine,
    StorageManager,
)


TEST_DIR = Path(__file__).parent.absolute()
TEST_STORAGE = TEST_DIR / "test_sm_storage"


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up storage and reset singleton"""
    TEST_STORAGE.mkdir(parents=True, exist_ok=True)
    StorageManager.reset_instance()
    yield
    StorageManager.reset_instance()
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)


class TestStorageManagerSingleton:
    """Tests for singleton behavior"""

    def test_get_instance_returns_same_object(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        StorageManager.set_instance(manager)
        assert StorageManager.get_instance() is manager

    def test_set_instance_replaces(self):
        m1 = StorageManager(local_storage_root=TEST_STORAGE)
        m2 = StorageManager(local_storage_root=TEST_STORAGE)
        StorageManager.set_instance(m1)
        StorageManager.set_instance(m2)
        assert StorageManager.get_instance() is m2

    def test_reset_instance(self):
        m = StorageManager(local_storage_root=TEST_STORAGE)
        StorageManager.set_instance(m)
        StorageManager.reset_instance()
        # get_instance creates a new default one
        new = StorageManager.get_instance()
        assert new is not m


class TestStorageManagerLocalFallback:
    """Tests for local storage fallback"""

    def test_default_engine_returns_file_storage(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        engine = manager.get_default_engine()
        assert isinstance(engine, FileStorageEngine)

    def test_default_engine_caches(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        e1 = manager.get_default_engine()
        e2 = manager.get_default_engine()
        assert e1 is e2

    def test_no_config_no_local_raises(self):
        manager = StorageManager(local_storage_root=None)
        with pytest.raises(StorageException):
            manager.get_default_engine()

    def test_get_engine_for_attachment_local(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        engine, config_id = manager.get_engine_for_attachment(None)
        assert isinstance(engine, FileStorageEngine)
        assert config_id is None

    def test_get_engine_for_attachment_unknown_config_raises(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        with pytest.raises(StorageException):
            manager.get_engine("nonexistent-config")

    def test_clear_cache(self):
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        e1 = manager.get_default_engine()
        manager.clear_cache()
        e2 = manager.get_default_engine()
        # After clearing cache, a new engine is created
        assert e1 is not e2

    def test_local_engine_can_save_and_read(self):
        """End-to-end: StorageManager -> FileStorageEngine -> save/read"""
        manager = StorageManager(local_storage_root=TEST_STORAGE)
        engine = manager.get_default_engine()
        result = engine.save_file(b"test data", "test.txt")
        assert engine.get_file(result.storage_path) == b"test data"
