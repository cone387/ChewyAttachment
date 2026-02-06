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
- 📁 **存储灵活**: 默认存储在 media/attachments 目录，可自定义路径
- 📁 **完整功能**: 文件上传、下载、删除、列表查询
- 🔐 **简化权限**: 基于 owner_id 的权限模型，支持 public/private 访问级别
- 🎯 **认证解耦**: 通过外部注入 user_id 实现认证解耦
- 📝 **Markdown 友好**: 返回 Markdown 格式的文件引用链接
- 🗄️ **轻量存储**: 数据库仅存元信息，文件存储于本地文件系统或云存储
- 🔌 **即插即用**: 独立于具体业务表的通用数据模型
- 🎨 **RESTful API**: 标准化的 API 设计
- 💚 **健康检查**: 内置健康检查接口，监控数据库和存储状态
- 📊 **存储统计**: 提供存储使用量统计接口

## 📦 安装

```bash
# 使用 pip 安装
pip install chewy-attachment

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

# 或从源码安装
git clone https://github.com/cone387/ChewyAttachment.git
cd ChewyAttachment
pip install -e .
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

# ChewyAttachment 配置（可选）
# 如果不配置，将使用默认值
CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "file",  # 或 "django" (用于 S3)
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",  # 本地存储路径
}

# S3 存储配置（可选）
# 如果使用 S3，需要配置以下设置
# AWS_ACCESS_KEY_ID = 'your-access-key'
# AWS_SECRET_ACCESS_KEY = 'your-secret-key'
# AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
# AWS_S3_REGION_NAME = 'us-east-1'
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

> **说明**：
> - **数据库**：自动使用 Django 项目的默认数据库配置（`DATABASES['default']`），无需单独配置
> - **存储路径**：默认为 `BASE_DIR / "media" / "attachments"`，文件存储在项目目录的 media/attachments 文件夹中

2. **配置 URL**

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
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
from chewy_attachment.fastapi_app import dependencies, router

app = FastAPI()

# 配置数据库和存储（使用项目自己的数据库配置）
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = "sqlite:///./your_app.db"  # 或使用 PostgreSQL/MySQL 等
STORAGE_ROOT = BASE_DIR / "media" / "attachments"  # 默认存储路径

# 初始化 ChewyAttachment
dependencies.configure(DATABASE_URL, STORAGE_ROOT)

# 挂载路由
app.include_router(router, prefix="/api/attachments")

# 添加用户认证中间件（示例）
@app.middleware("http")
async def add_user_context(request: Request, call_next):
    # 从你的认证系统获取用户 ID
    request.state.user_id = "your-user-id"  # 替换为实际的用户认证逻辑
    response = await call_next(request)
    return response
```

> **说明**：
> - **数据库**：通过 `configure()` 方法传入数据库连接，支持任意 SQLAlchemy 兼容的数据库
> - **存储路径**：默认为 `BASE_DIR / "media" / "attachments"`，文件存储在项目目录的 media/attachments 文件夹中
> - **用户认证**：通过中间件设置 `request.state.user_id` 实现认证解耦

## 📚 API 文档

### Django API

#### 上传文件

```bash
POST /api/attachments/files/
Content-Type: multipart/form-data

参数:
- file: 文件对象 (必须)
- is_public: boolean (可选, 默认: false)
- owner_id: string (可选, 由认证系统自动填充)
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
  "created_at": "2026-01-14 10:30:00",
  "preview_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/preview/"
}
```

> **注意**: `preview_url` 返回相对路径，根据实际路由配置动态生成。

#### 获取文件列表

```bash
GET /api/attachments/files/

查询参数:
- page: 页码 (默认: 1)
- page_size: 每页数量 (默认: 20, 最大: 100)
```

**返回示例:**
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/attachments/files/?page=2",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "original_name": "example.jpg",
      "mime_type": "image/jpeg",
      "size": 102400,
      "owner_id": "123",
      "is_public": true,
      "created_at": "2026-01-14 10:30:00",
      "preview_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/preview/"
    }
  ]
}
```

#### 获取文件详情

```bash
GET /api/attachments/files/{attachment_id}/
```

**返回示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_name": "example.jpg",
  "mime_type": "image/jpeg",
  "size": 102400,
  "owner_id": "123",
  "is_public": true,
  "created_at": "2026-01-14 10:30:00",
  "preview_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/preview/"
}
```

#### 预览文件

```bash
GET /api/attachments/files/{attachment_id}/preview/
```

在浏览器中直接预览文件（inline 模式），图片会直接显示。

#### 下载文件

```bash
GET /api/attachments/files/{attachment_id}/content/
```

强制下载文件（attachment 模式）。

#### 删除文件

```bash
DELETE /api/attachments/files/{attachment_id}/
```

#### 健康检查

```bash
GET /api/attachments/health/
```

检查服务健康状态，包括数据库连接和存储引擎状态。

**返回示例:**
```json
{
  "status": "healthy",
  "version": "0.5.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "storage": {
      "status": "healthy",
      "type": "FileStorageEngine",
      "message": "Storage engine initialized"
    }
  }
}
```

#### 存储统计

```bash
GET /api/attachments/stats/
```

获取当前用户的存储使用统计。管理员可添加 `?global=true` 查看全局统计。

**返回示例:**
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

### FastAPI API

#### 上传文件

```bash
POST /api/attachments/files/
Content-Type: multipart/form-data

参数:
- file: 文件对象 (必须)
- is_public: boolean (可选, 默认: false)
```

#### 获取文件列表

```bash
GET /api/attachments/files/

查询参数:
- page: 页码 (默认: 1)
- page_size: 每页数量 (默认: 20, 最大: 100)
```

**返回示例:**
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "original_name": "example.jpg",
      "mime_type": "image/jpeg",
      "size": 102400,
      "owner_id": "123",
      "is_public": true,
      "created_at": "2026-01-14T10:30:00",
      "preview_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/preview"
    }
  ]
}
```

#### 获取文件详情

```bash
GET /api/attachments/files/{attachment_id}
```

#### 预览文件

```bash
GET /api/attachments/files/{attachment_id}/preview
```

#### 下载文件

```bash
GET /api/attachments/files/{attachment_id}/content
```

#### 删除文件

```bash
DELETE /api/attachments/files/{attachment_id}
```

## 🔐 权限模型

- **Public 文件**: 所有人可读，仅所有者可删除
- **Private 文件**: 仅所有者可读可删除
- **Owner ID**: 通过外部认证系统注入，实现认证解耦

## 📁 数据模型

```python
class Attachment:
    id: str                # UUID 主键
    original_name: str     # 原始文件名
    storage_path: str      # 物理存储路径
    mime_type: str         # MIME 类型
    size: int              # 文件大小(字节)
    owner_id: str          # 所有者 ID
    is_public: bool        # 访问级别
    created_at: datetime   # 创建时间
```

> **数据库表名**: 默认为 `chewy_attachments`，可通过自定义模型修改

## 🛠️ 配置选项

### Django 配置

```python
# settings.py

# ChewyAttachment 配置
CHEWY_ATTACHMENT = {
    # 存储引擎 (可选, 默认: "file")
    # "file": 本地文件存储
    # "django": 使用 Django 存储系统 (支持 django-storages)
    "STORAGE_ENGINE": "file",
    
    # 存储根目录 (可选, 默认: BASE_DIR / "media" / "attachments")
    # 仅在 STORAGE_ENGINE="file" 时使用
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",
    
    # 文件大小限制 (可选, 默认: 10MB)
    "MAX_FILE_SIZE": 10 * 1024 * 1024,
    
    # 允许的文件扩展名 (可选, 默认: 无限制)
    "ALLOWED_EXTENSIONS": [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".pdf", ".doc", ".docx", ".txt", ".zip",
    ],
    
    # 时间格式 (可选, 默认: "%Y-%m-%d %H:%M:%S")
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    
    # 自定义权限类 (可选)
    "PERMISSION_CLASSES": [
        "chewy_attachment.django_app.permissions.IsAuthenticatedForUpload",
        "chewy_attachment.django_app.permissions.IsOwnerOrPublicReadOnly",
    ],
}

# 自定义模型 (可选, 类似 AUTH_USER_MODEL)
# CHEWY_ATTACHMENT_MODEL = 'myapp.MyAttachment'
```

#### S3 云存储配置

ChewyAttachment 通过 django-storages 支持 AWS S3 和兼容 S3 的云存储服务：

```python
# settings.py

# 1. 安装依赖: pip install 'chewy-attachment[django-s3]'

# 2. 添加到 INSTALLED_APPS
INSTALLED_APPS = [
    # ...
    'storages',  # django-storages
    'chewy_attachment.django_app',
]

# 3. AWS S3 配置
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# S3 设置
AWS_DEFAULT_ACL = 'private'  # 文件默认私有
AWS_S3_FILE_OVERWRITE = False  # 不覆盖同名文件
AWS_QUERYSTRING_AUTH = True  # 使用签名 URL
AWS_QUERYSTRING_EXPIRE = 3600  # 签名 URL 1小时过期

# 使用 S3 作为默认文件存储
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 4. ChewyAttachment 配置
CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "django",  # 使用 Django 存储系统
    "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 10MB
    "ALLOWED_EXTENSIONS": [".jpg", ".png", ".pdf", ".txt"],
}
```

**测试 S3 配置：**

```bash
# 测试 S3 连接和基本操作
python manage.py test_s3_storage

# 测试并清理测试文件
python manage.py test_s3_storage --cleanup
```

**详细 S3 配置指南：** 查看 [S3 存储配置文档](docs/S3_STORAGE.md)

**配置说明：**

- `STORAGE_ROOT`: 文件存储的物理路径（可选，默认为 `BASE_DIR / "media" / "attachments"`）
- `DATETIME_FORMAT`: API 返回的时间字段格式
- `PERMISSION_CLASSES`: 自定义 DRF 权限类列表
- `CHEWY_ATTACHMENT_MODEL`: 自定义附件模型（类似 Django 的 `AUTH_USER_MODEL`）

#### 自定义表名和模型

ChewyAttachment 支持模型交换机制，类似于 Django 的 `AUTH_USER_MODEL`：

```python
# myapp/models.py
from chewy_attachment.django_app.models import AttachmentBase

class MyAttachment(AttachmentBase):
    """自定义附件模型"""
    
    # 可以添加额外字段
    category = models.CharField(max_length=50, blank=True, verbose_name="分类")
    
    class Meta(AttachmentBase.Meta):
        db_table = "my_custom_attachments"  # 自定义表名
        abstract = False
        app_label = 'myapp'

# settings.py
CHEWY_ATTACHMENT_MODEL = 'myapp.MyAttachment'
```

**使用步骤：**

1. 创建自定义模型（继承 `AttachmentBase`）
2. 在 settings.py 中设置 `CHEWY_ATTACHMENT_MODEL`
3. 运行 `python manage.py makemigrations myapp`
4. 运行 `python manage.py migrate`

**优势：**

- ✅ **标准Django机制**：使用Django官方推荐的模型交换方式
- ✅ **避免冲突**：每个项目使用自己的模型，不会有多项目冲突
- ✅ **自动适配**：库的视图和序列化器自动使用指定模型
- ✅ **灵活扩展**：可以添加任意自定义字段和方法

#### 自定义权限类示例

```python
# myapp/permissions.py
from rest_framework import permissions
from chewy_attachment.django_app.models import Attachment
from chewy_attachment.core.permissions import PermissionChecker

class CustomAttachmentPermission(permissions.BasePermission):
    """
    自定义附件权限类
    
    示例: 管理员可以访问所有文件,普通用户只能访问自己的文件
    """
    
    def has_object_permission(self, request, view, obj: Attachment):
        # 管理员拥有所有权限
        if request.user and request.user.is_staff:
            return True
        
        # 使用核心权限检查器
        user_context = Attachment.get_user_context(request)
        file_metadata = obj.to_file_metadata()
        
        if request.method in permissions.SAFE_METHODS:
            return PermissionChecker.can_view(file_metadata, user_context)
        
        if request.method == "DELETE":
            return PermissionChecker.can_delete(file_metadata, user_context)
        
        return False

# settings.py
CHEWY_ATTACHMENT = {
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",
    "PERMISSION_CLASSES": [
        "chewy_attachment.django_app.permissions.IsAuthenticatedForUpload",
        "myapp.permissions.CustomAttachmentPermission",
    ],
}
```

### FastAPI 配置

```python
from chewy_attachment.core.storage import FileStorage

# 自定义存储路径
storage = FileStorage(base_path="/custom/path/media")
```

## 📂 项目结构

```
ChewyAttachment/
├── chewy_attachment/
│   ├── core/                 # 核心功能模块
│   │   ├── schemas.py        # 数据模式
│   │   ├── storage.py        # 文件存储
│   │   ├── permissions.py    # 权限控制
│   │   └── utils.py          # 工具函数
│   ├── django_app/           # Django 应用
│   │   ├── models.py         # Django 模型
│   │   ├── views.py          # Django 视图
│   │   ├── serializers.py    # DRF 序列化器
│   │   └── urls.py           # URL 配置
│   └── fastapi_app/          # FastAPI 应用
│       ├── models.py         # SQLAlchemy 模型
│       ├── router.py         # API 路由
│       ├── crud.py           # CRUD 操作
│       └── dependencies.py   # 依赖注入
├── examples/                 # 示例项目
│   ├── django_example/       # Django 示例
│   └── fastapi_example/      # FastAPI 示例
└── pyproject.toml            # 项目配置
```

## 🧪 运行测试

```bash
# 安装测试依赖
pip install chewy-attachment[dev]

# 运行所有测试
pytest tests/ -v

# 运行并显示覆盖率
pytest tests/ --cov=chewy_attachment --cov-report=html

# 运行特定模块测试
pytest tests/test_core/ -v
```

详细测试指南请参阅 [docs/TESTING.md](docs/TESTING.md)。

## 📖 更多文档

- [S3 存储配置指南](docs/S3_STORAGE.md) - 单一 S3 存储配置
- [多 S3 存储配置](docs/MULTI_S3_STORAGE.md) - 多存储配置、动态切换、数据迁移
- [测试指南](docs/TESTING.md) - 测试框架和示例

## 📝 示例代码

查看 `examples/` 目录获取完整的示例项目：

- [Django 示例](examples/django_example/)
- [FastAPI 示例](examples/fastapi_example/)

### 运行 Django 示例

```bash
# 克隆项目（如果还没有）
git clone https://github.com/cone387/ChewyAttachment.git
cd ChewyAttachment

# 使用 uv 安装依赖（会自动创建 .venv 虚拟环境）
uv sync

# 进入 Django 示例目录
cd examples/django_example

# 运行迁移
uv run python manage.py migrate

# 创建超级用户（可选）
uv run python manage.py createsuperuser

# 启动开发服务器
uv run python manage.py runserver

# 访问
# - API: http://localhost:8000/api/attachments/
# - Admin: http://localhost:8000/admin/
```

### 运行 FastAPI 示例

```bash
# 克隆项目（如果还没有）
git clone https://github.com/cone387/ChewyAttachment.git
cd ChewyAttachment

# 使用 uv 安装依赖（会自动创建 .venv 虚拟环境）
uv sync

# 启动 FastAPI 应用
uv run python examples/fastapi_example/main.py

# 访问
# - API: http://localhost:8000/api/attachments/
# - Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 👤 作者

- GitHub: [@cone387](https://github.com/cone387)

## 🔗 相关链接

- [项目主页](https://github.com/cone387/ChewyAttachment)
- [问题反馈](https://github.com/cone387/ChewyAttachment/issues)
