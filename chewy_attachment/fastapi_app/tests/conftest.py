"""pytest configuration for FastAPI tests"""

import shutil
from pathlib import Path
from typing import Callable, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from chewy_attachment.core.schemas import UserContext
from chewy_attachment.fastapi_app import dependencies
from chewy_attachment.fastapi_app.router import router

TEST_DIR = Path(__file__).parent.absolute()
TEST_STORAGE = TEST_DIR / "test_storage"
TEST_DB = TEST_DIR / "test.db"


_current_user_id: Optional[str] = None


def _get_test_current_user() -> UserContext:
    """Get current user for testing"""
    if _current_user_id is not None:
        return UserContext.authenticated(_current_user_id)
    return UserContext.anonymous()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment"""
    TEST_STORAGE.mkdir(parents=True, exist_ok=True)

    yield

    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine"""
    db_path = TEST_DIR / f"test_{id(object())}.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)

    yield engine

    engine.dispose()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db_session(db_engine):
    """Create test database session"""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def app(db_engine):
    """Create test FastAPI app"""
    test_app = FastAPI()

    dependencies._engine = db_engine
    dependencies._storage_root = TEST_STORAGE

    test_app.include_router(router)

    test_app.dependency_overrides[dependencies.get_current_user] = _get_test_current_user

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def user1_id():
    """User 1 ID"""
    return "user-1-test-id"


@pytest.fixture
def user2_id():
    """User 2 ID"""
    return "user-2-test-id"


@pytest.fixture
def set_current_user() -> Callable[[Optional[str]], None]:
    """Fixture to set current user for testing"""
    def _set_user(user_id: Optional[str]):
        global _current_user_id
        _current_user_id = user_id

    yield _set_user

    global _current_user_id
    _current_user_id = None
