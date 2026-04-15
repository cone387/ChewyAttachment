# ChewyAttachment

[![PyPI version](https://badge.fury.io/py/chewy-attachment.svg)](https://badge.fury.io/py/chewy-attachment)
[![Python Versions](https://img.shields.io/pypi/pyversions/chewy-attachment.svg)](https://pypi.org/project/chewy-attachment/)
[![License](https://img.shields.io/pypi/l/chewy-attachment.svg)](https://github.com/cone387/ChewyAttachment/blob/master/LICENSE)
[![Downloads](https://pepy.tech/badge/chewy-attachment)](https://pepy.tech/project/chewy-attachment)

🚀 通用文件/附件管理服务 - 支持 Django & FastAPI 双框架

## 📖 简介

ChewyAttachment 是一个通用的文件/附件管理插件，提供开箱即用的文件上传、下载、删除功能。支持作为独立的 Django 应用或 FastAPI 可插拔模块运行，适合个人自托管场景，可被多个业务系统复用。

## ✨ 核心特性

- 🔄 **双框架支持**: 同时支持 Django 和 FastAPI
- ☁️ **多存储支持**: 本地文件存储 + AWS S3 云存储（支持 MinIO、阿里云 OSS 等 S3 兼容服务）
- 🔀 **多 S3 配置**: 支持动态切换多个 S3 存储配置，不同用户/附件可使用不同存储
- 🔄 **数据迁移**: 支持在不同存储配置之间迁移文件，用户切换存储后可同步历史数据
- 🗄️ **数据库灵活**: Django 自动使用项目默认数据库，FastAPI 支持任意 SQLAlchemy 兼容数据库
- 📁 **完整功能**: 文件上传、下载、预览、删除、列表查询
- 🔐 **权限控制**: 基于 owner_id 的权限模型，支持 public/private 访问级别
- 🛡️ **安全校验**: 文件大小限制、扩展名白名单、MIME 内容校验（防止伪装上传）
- 🎯 **认证解耦**: 通过外部注入 user_id 实现认证解耦
-  **即插即用**: 独立于具体业务表的通用数据模型，支持 Django 模型交换
- 💚 **健康检查**: 内置健康检查接口，监控数据库和存储状态
- 📊 **存储统计**: 提供存储使用量统计接口

## 📦 安装

```bash
# 安装 Django 支持
pip install chewy-attachment[django]

# 安装 Django + S3 支持
pip install chewy-attachment[django-s3]

# 安装 FastAPI 支持
pip install chewy-attachment[fastapi]

# 安装 FastAPI + S3 支持
pip install chewy-attachment[fastapi-s3]

# 安装全部功能(开发)
pip install chewy-attachment[dev]
```

## 🚀 快速开始

### Django 集成

1. **添加到 INSTALLED_APPS**

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'storages',  # 如果使用 S3 存储，需要添加
    'chewy_attachment.django_app',
]

# ChewyAttachment 配置（可选，以下均为默认值）
CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "file",                          # 或 "django" (用于 S3)
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",
}
```

2. **配置 URL**

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('api/attachments/', include('chewy_attachment.django_app.urls')),
]
```

3. **运行迁移**

```bash
python manage.py migrate
```

### FastAPI 集成

```python
from pathlib import Path
from fastapi import FastAPI, Request
from chewy_attachment.fastapi_app import router, health_router
from chewy_attachment.fastapi_app.dependencies import configure

app = FastAPI()

# 初始化
configure(
    database_url="sqlite:///./app.db",
    storage_root=Path("media/attachments"),
)

# 挂载路由
app.include_router(router, prefix="/api/attachments")
app.include_router(health_router, prefix="/api/attachments")

# 用户认证中间件（示例）
@app.middleware("http")
async def add_user_context(request: Request, call_next):
    request.state.user_id = "your-user-id"  # 替换为实际认证逻辑
    return await call_next(request)
```

## 📚 API 文档

### 端点一览

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /files/ | 上传文件 | 必须 |
| GET | /files/ | 文件列表（分页） | 可选 |
| GET | /files/{id}/ | 文件元信息 | 可选 |
| GET | /files/{id}/content/ | 下载文件 | 可选 |
| GET | /files/{id}/preview/ | 预览文件 | 可选 |
| DELETE | /files/{id}/ | 删除文件 | 必须 |
| GET | /health/ | 健康检查 | 无 |
| GET | /stats/ | 存储统计 | 必须 |

> FastAPI 端点不带尾部斜杠（如 `/files`、`/files/{id}/content`）。

### 上传文件

```bash
POST /files/
Content-Type: multipart/form-data

参数:
- file: 文件对象 (必须)
- is_public: boolean (可选, 默认: false)
- storage_config_id: string (可选, S3 存储配置 ID)
```

**返回示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_name": "example.jpg",
  "mime_type": "image/jpeg",
  "size": 102400,
  "owner_id": "123",
  "is_public": false,
  "storage_config_id": null,
  "created_at": "2026-01-14 10:30:00",
  "preview_url": "/api/attachments/files/550e8400.../preview/",
  "download_url": "/api/attachments/files/550e8400.../content/",
  "file_url": "/api/attachments/files/550e8400.../content/"
}
```

> `file_url` 对本地存储等于 `download_url`；对 S3 存储返回签名 URL。

### 文件列表

```bash
GET /files/?page=1&page_size=20
```

**Django 返回:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/attachments/files/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

**FastAPI 返回:**
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [ ... ]
}
```

### 健康检查

```bash
GET /health/
```

```json
{
  "status": "healthy",
  "version": "0.5.1",
  "checks": {
    "database": { "status": "healthy", "message": "Database connection successful" },
    "storage": { "status": "healthy", "type": "FileStorageEngine", "message": "Storage engine initialized" }
  }
}
```

### 存储统计

```bash
GET /stats/              # 当前用户统计
GET /stats/?global=true  # 全局统计（管理员）
```

```json
{
  "scope": "user",
  "user_id": "123",
  "total_files": 42,
  "total_size": 104857600,
  "total_size_human": "100.00 MB",
  "by_mime_type": [
    {"mime_type": "image/jpeg", "count": 20, "size": 52428800, "size_human": "50.00 MB"}
  ],
  "by_storage": [
    {"storage_config_id": "local", "count": 42, "size": 104857600, "size_human": "100.00 MB"}
  ]
}
```

## 🔐 权限模型

| 操作 | 规则 |
|------|------|
| 查看/下载 | `is_public=True` 或 `owner_id == 当前用户` |
| 删除 | 仅 `owner_id == 当前用户` |

## 📁 数据模型

```python
class Attachment:
    id: UUID               # 主键
    original_name: str     # 原始文件名
    storage_path: str      # 存储路径
    mime_type: str         # MIME 类型
    size: int              # 文件大小(字节)
    owner_id: str          # 所有者 ID
    is_public: bool        # 访问级别
    storage_config_id: str # S3 存储配置 ID (可空, 空=本地存储)
    created_at: datetime   # 创建时间
```

> 默认表名 `chewy_attachments`，可通过自定义模型修改。

## 🛠️ 配置选项

### Django 配置

```python
CHEWY_ATTACHMENT = {
    # 存储引擎: "file" (本地) 或 "django" (django-storages)
    "STORAGE_ENGINE": "file",

    # 本地存储路径 (STORAGE_ENGINE="file" 时使用)
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",

    # 文件大小限制 (默认 10MB)
    "MAX_FILE_SIZE": 10 * 1024 * 1024,

    # 允许的文件扩展名 (默认无限制)
    "ALLOWED_EXTENSIONS": [".jpg", ".png", ".pdf", ".txt"],

    # MIME 内容校验 — 检测伪装文件 (默认关闭)
    "VALIDATE_MIME_CONTENT": False,

    # 时间格式
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",

    # 自定义 DRF 权限类
    "PERMISSION_CLASSES": [
        "IsAuthenticatedForUpload",
        "IsOwnerOrPublicReadOnly",
    ],

    # 多 S3 存储配置提供者 (高级)
    # "STORAGE_CONFIG_PROVIDER": "myapp.storage.MyProvider",
}

# 自定义模型 (类似 AUTH_USER_MODEL)
# CHEWY_ATTACHMENT_MODEL = 'myapp.MyAttachment'
```

#### S3 云存储

```python
# 1. pip install 'chewy-attachment[django-s3]'
# 2. INSTALLED_APPS 添加 'storages'
# 3. 配置 AWS

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = 'us-east-1'
AWS_DEFAULT_ACL = 'private'
AWS_QUERYSTRING_AUTH = True
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "django",
}
```

详细指南: [S3 存储配置](docs/S3_STORAGE.md) | [多 S3 存储配置](docs/MULTI_S3_STORAGE.md)

### FastAPI 配置

```python
from chewy_attachment.fastapi_app.dependencies import configure

# 基础配置
configure(
    database_url="sqlite:///./app.db",
    storage_root="./media/attachments",
)

# 带 S3 多存储配置
from chewy_attachment.core.storage import StorageConfigProvider
configure(
    database_url="sqlite:///./app.db",
    storage_root="./media/attachments",           # 本地存储回退
    storage_config_provider=MyS3ConfigProvider(),  # 自定义 S3 配置提供者
)
```

#### 自定义模型 (Django)

```python
from chewy_attachment.django_app.models import AttachmentBase

class MyAttachment(AttachmentBase):
    category = models.CharField(max_length=50, blank=True)

    class Meta(AttachmentBase.Meta):
        db_table = "my_attachments"
        abstract = False
        app_label = 'myapp'

# settings.py
CHEWY_ATTACHMENT_MODEL = 'myapp.MyAttachment'
```

#### 自定义权限类 (Django)

```python
from rest_framework import permissions
from chewy_attachment.core.permissions import PermissionChecker

class AdminOrOwnerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        user_context = obj.get_user_context(request)
        file_metadata = obj.to_file_metadata()
        if request.method in permissions.SAFE_METHODS:
            return PermissionChecker.can_view(file_metadata, user_context)
        return PermissionChecker.can_delete(file_metadata, user_context)
```

## 📂 项目结构

```
chewy_attachment/
├── core/                     # 框架无关的核心层
│   ├── storage.py            # 存储引擎 (File/Django/S3/StorageManager)
│   ├── schemas.py            # 数据结构
│   ├── permissions.py        # 权限检查
│   ├── exceptions.py         # 异常定义
│   └── utils.py              # 工具函数
├── django_app/               # Django 实现
│   ├── models.py             # 数据模型 (支持模型交换)
│   ├── views.py              # ViewSet + 健康检查 + 统计
│   ├── serializers.py        # DRF 序列化器
│   ├── storage.py            # 存储配置工具
│   ├── admin.py              # Admin 界面
│   ├── permissions.py        # DRF 权限类
│   ├── urls.py               # URL 路由
│   └── management/commands/  # 管理命令
└── fastapi_app/              # FastAPI 实现
    ├── models.py             # SQLModel 模型
    ├── router.py             # API 路由 + 健康检查 + 统计
    ├── schemas.py            # Pydantic 响应模型
    ├── crud.py               # CRUD 操作
    └── dependencies.py       # 依赖注入
```

## 🧪 运行测试

```bash
# 安装开发依赖
pip install chewy-attachment[dev]

# 运行所有测试
pytest chewy_attachment/ tests/ -v

# 运行并显示覆盖率
pytest chewy_attachment/ tests/ --cov=chewy_attachment --cov-report=html
```

详细测试指南: [docs/TESTING.md](docs/TESTING.md)

## 📖 更多文档

- [S3 存储配置指南](docs/S3_STORAGE.md)
- [多 S3 存储配置](docs/MULTI_S3_STORAGE.md)
- [测试指南](docs/TESTING.md)

## 📝 示例项目

- [Django 示例](examples/django_example/) — 基础本地存储
- [Django S3 示例](examples/django_s3_example/) — S3 云存储
- [FastAPI 示例](examples/fastapi_example/) — FastAPI 集成

```bash
# 运行 Django 示例
cd examples/django_example
uv run python manage.py migrate
uv run python manage.py runserver

# 运行 FastAPI 示例
uv run python examples/fastapi_example/main.py
```

## 📄 License

MIT License — [@cone387](https://github.com/cone387)
