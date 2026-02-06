# 测试指南

本文档介绍如何为 ChewyAttachment 编写和运行测试。

## 测试框架

ChewyAttachment 使用以下测试工具：

- **pytest**: Python 测试框架
- **pytest-cov**: 代码覆盖率
- **pytest-asyncio**: 异步测试支持
- **pytest-django**: Django 集成测试
- **httpx**: FastAPI 测试客户端

## 安装测试依赖

```bash
# 安装 Django 测试依赖
pip install 'chewy-attachment[test-django]'

# 安装 FastAPI 测试依赖
pip install 'chewy-attachment[test-fastapi]'

# 安装全部开发依赖
pip install 'chewy-attachment[dev]'
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行并显示覆盖率
pytest --cov=chewy_attachment --cov-report=html

# 运行特定测试文件
pytest tests/test_storage.py

# 运行特定测试函数
pytest tests/test_storage.py::test_file_upload

# 显示详细输出
pytest -v
```

## 测试目录结构

建议的测试目录结构：

```
tests/
├── conftest.py              # 共享 fixtures
├── test_core/
│   ├── test_storage.py      # 存储引擎测试
│   ├── test_permissions.py  # 权限测试
│   └── test_utils.py        # 工具函数测试
├── test_django/
│   ├── conftest.py          # Django fixtures
│   ├── test_views.py        # API 视图测试
│   └── test_models.py       # 模型测试
└── test_fastapi/
    ├── conftest.py          # FastAPI fixtures
    └── test_router.py       # 路由测试
```

## 编写测试示例

### 1. 核心存储引擎测试

```python
# tests/test_core/test_storage.py
import pytest
from pathlib import Path
from chewy_attachment.core.storage import FileStorageEngine

@pytest.fixture
def storage_root(tmp_path):
    """创建临时存储目录"""
    return tmp_path / "attachments"

@pytest.fixture
def storage_engine(storage_root):
    """创建存储引擎实例"""
    return FileStorageEngine(storage_root)

class TestFileStorageEngine:
    def test_save_file(self, storage_engine):
        """测试文件保存"""
        content = b"Hello, World!"
        result = storage_engine.save_file(content, "test.txt")
        
        assert result.storage_path is not None
        assert result.size == len(content)
        assert result.mime_type == "text/plain"
    
    def test_get_file(self, storage_engine):
        """测试文件读取"""
        content = b"Test content"
        result = storage_engine.save_file(content, "test.txt")
        
        retrieved = storage_engine.get_file(result.storage_path)
        assert retrieved == content
    
    def test_delete_file(self, storage_engine):
        """测试文件删除"""
        content = b"To be deleted"
        result = storage_engine.save_file(content, "delete_me.txt")
        
        storage_engine.delete_file(result.storage_path)
        assert not storage_engine.file_exists(result.storage_path)
    
    def test_file_not_found(self, storage_engine):
        """测试文件不存在的情况"""
        from chewy_attachment.core.exceptions import StorageException
        
        with pytest.raises(StorageException):
            storage_engine.get_file("nonexistent/path.txt")
```

### 2. 权限检查测试

```python
# tests/test_core/test_permissions.py
import pytest
from datetime import datetime
from chewy_attachment.core.permissions import PermissionChecker
from chewy_attachment.core.schemas import FileMetadata, UserContext

@pytest.fixture
def public_file():
    """公开文件"""
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
    """私有文件"""
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

class TestPermissionChecker:
    def test_anonymous_can_view_public_file(self, public_file):
        """匿名用户可以查看公开文件"""
        user = UserContext.anonymous()
        assert PermissionChecker.can_view(public_file, user) is True
    
    def test_anonymous_cannot_view_private_file(self, private_file):
        """匿名用户不能查看私有文件"""
        user = UserContext.anonymous()
        assert PermissionChecker.can_view(private_file, user) is False
    
    def test_owner_can_view_private_file(self, private_file):
        """所有者可以查看自己的私有文件"""
        user = UserContext.authenticated("user-001")
        assert PermissionChecker.can_view(private_file, user) is True
    
    def test_other_user_cannot_view_private_file(self, private_file):
        """其他用户不能查看私有文件"""
        user = UserContext.authenticated("user-002")
        assert PermissionChecker.can_view(private_file, user) is False
    
    def test_only_owner_can_delete(self, public_file):
        """只有所有者可以删除文件"""
        owner = UserContext.authenticated("user-001")
        other = UserContext.authenticated("user-002")
        
        assert PermissionChecker.can_delete(public_file, owner) is True
        assert PermissionChecker.can_delete(public_file, other) is False
```

### 3. Django API 测试

```python
# tests/test_django/conftest.py
import pytest
from django.contrib.auth import get_user_model

@pytest.fixture
def user(db):
    """创建测试用户"""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
    )

@pytest.fixture
def api_client():
    """创建 API 客户端"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    """创建已认证的 API 客户端"""
    api_client.force_authenticate(user=user)
    return api_client
```

```python
# tests/test_django/test_views.py
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
class TestAttachmentViewSet:
    def test_upload_file(self, authenticated_client):
        """测试文件上传"""
        file = SimpleUploadedFile(
            "test.txt",
            b"Test content",
            content_type="text/plain",
        )
        
        response = authenticated_client.post(
            "/api/attachments/files/",
            {"file": file, "is_public": False},
            format="multipart",
        )
        
        assert response.status_code == 201
        assert response.data["original_name"] == "test.txt"
        assert response.data["mime_type"] == "text/plain"
    
    def test_list_files(self, authenticated_client):
        """测试文件列表"""
        response = authenticated_client.get("/api/attachments/files/")
        
        assert response.status_code == 200
        assert "results" in response.data
    
    def test_health_check(self, api_client):
        """测试健康检查接口"""
        response = api_client.get("/api/attachments/health/")
        
        assert response.status_code == 200
        assert response.data["status"] == "healthy"
        assert "version" in response.data
```

### 4. FastAPI API 测试

```python
# tests/test_fastapi/conftest.py
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session

@pytest.fixture
def test_db(tmp_path):
    """创建测试数据库"""
    db_path = tmp_path / "test.db"
    return f"sqlite:///{db_path}"

@pytest.fixture
def storage_root(tmp_path):
    """创建测试存储目录"""
    return tmp_path / "attachments"

@pytest.fixture
def app(test_db, storage_root):
    """创建测试应用"""
    from fastapi import FastAPI, Request
    from chewy_attachment.fastapi_app import router, health_router
    from chewy_attachment.fastapi_app.dependencies import configure
    
    app = FastAPI()
    configure(test_db, storage_root)
    
    @app.middleware("http")
    async def add_user(request: Request, call_next):
        request.state.user_id = "test-user-001"
        return await call_next(request)
    
    app.include_router(router, prefix="/api/attachments")
    app.include_router(health_router, prefix="/api/attachments")
    
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)
```

```python
# tests/test_fastapi/test_router.py
import pytest

class TestAttachmentRouter:
    def test_upload_file(self, client):
        """测试文件上传"""
        response = client.post(
            "/api/attachments/files",
            files={"file": ("test.txt", b"Test content", "text/plain")},
            data={"is_public": "false"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["original_name"] == "test.txt"
    
    def test_list_files(self, client):
        """测试文件列表"""
        response = client.get("/api/attachments/files")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/attachments/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_storage_stats(self, client):
        """测试存储统计"""
        response = client.get("/api/attachments/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_size" in data
```

### 5. S3 存储测试（使用 moto mock）

```python
# tests/test_core/test_s3_storage.py
import pytest

# 需要安装 moto: pip install moto[s3]
pytest.importorskip("moto")

import boto3
from moto import mock_aws
from chewy_attachment.core.storage import S3StorageEngine
from chewy_attachment.core.schemas import S3ConfigSchema

@pytest.fixture
def s3_config():
    """S3 配置"""
    return S3ConfigSchema(
        config_id="test-s3",
        bucket_name="test-bucket",
        access_key="testing",
        secret_key="testing",
        region="us-east-1",
        prefix="attachments",
    )

@pytest.fixture
def mock_s3(s3_config):
    """Mock S3 服务"""
    with mock_aws():
        # 创建 bucket
        client = boto3.client(
            "s3",
            region_name=s3_config.region,
            aws_access_key_id=s3_config.access_key,
            aws_secret_access_key=s3_config.secret_key,
        )
        client.create_bucket(Bucket=s3_config.bucket_name)
        yield

@pytest.fixture
def s3_engine(mock_s3, s3_config):
    """创建 S3 存储引擎"""
    return S3StorageEngine.from_config(s3_config)

class TestS3StorageEngine:
    def test_save_and_get_file(self, s3_engine):
        """测试 S3 文件保存和读取"""
        content = b"S3 test content"
        result = s3_engine.save_file(content, "test.txt")
        
        assert result.storage_path is not None
        
        retrieved = s3_engine.get_file(result.storage_path)
        assert retrieved == content
    
    def test_delete_file(self, s3_engine):
        """测试 S3 文件删除"""
        content = b"To be deleted"
        result = s3_engine.save_file(content, "delete.txt")
        
        s3_engine.delete_file(result.storage_path)
        assert not s3_engine.file_exists(result.storage_path)
    
    def test_get_presigned_url(self, s3_engine):
        """测试预签名 URL"""
        content = b"URL test"
        result = s3_engine.save_file(content, "url_test.txt")
        
        url = s3_engine.get_file_url(result.storage_path)
        assert "test-bucket" in url
        assert "url_test.txt" in url or result.storage_path in url
```

## 持续集成配置

### GitHub Actions 示例

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e '.[dev]'
      
      - name: Run tests
        run: |
          pytest --cov=chewy_attachment --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## 测试最佳实践

1. **隔离测试**: 每个测试应该独立运行，不依赖其他测试的状态
2. **使用 fixtures**: 利用 pytest fixtures 复用测试设置代码
3. **Mock 外部服务**: 使用 moto 等库 mock AWS 服务，避免真实 API 调用
4. **测试边界条件**: 包括空文件、大文件、特殊字符文件名等
5. **测试错误处理**: 确保异常情况被正确处理
6. **保持测试快速**: 避免不必要的 I/O 操作，使用内存数据库

## 代码覆盖率目标

建议的最低覆盖率目标：

| 模块 | 目标覆盖率 |
|------|-----------|
| core/storage.py | 90% |
| core/permissions.py | 95% |
| core/utils.py | 90% |
| django_app/views.py | 80% |
| fastapi_app/router.py | 80% |
