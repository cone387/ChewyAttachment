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
- 📁 **完整功能**: 文件上传、下载、删除、列表查询
- 🔐 **简化权限**: 基于 owner_id 的权限模型，支持 public/private 访问级别
- 🎯 **认证解耦**: 通过外部注入 user_id 实现认证解耦
- 📝 **Markdown 友好**: 返回 Markdown 格式的文件引用链接
- 🗄️ **轻量存储**: SQLite + 本地文件系统，数据库仅存元信息
- 🔌 **即插即用**: 独立于具体业务表的通用数据模型
- 🎨 **RESTful API**: 标准化的 API 设计

## 📦 安装

```bash
# 使用 pip 安装
pip install chewy-attachment

# 安装 Django 支持
pip install chewy-attachment[django]

# 安装 FastAPI 支持
pip install chewy-attachment[fastapi]

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
    'chewy_attachment.django_app',
]

# 配置文件存储
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

2. **配置 URL**

```python
# urls.py
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ...
    path('api/attachments/', include('chewy_attachment.django_app.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

3. **运行迁移**

```bash
python manage.py migrate
```

### FastAPI 集成

```python
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from chewy_attachment.fastapi_app.router import router as attachment_router
from chewy_attachment.fastapi_app.models import Base
from chewy_attachment.fastapi_app.dependencies import get_current_user_id

app = FastAPI()

# 数据库配置
engine = create_engine("sqlite:///./attachments.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 自定义用户认证
async def custom_get_user_id() -> int:
    # 实现你的用户认证逻辑
    return 1  # 示例

# 挂载路由
app.include_router(
    attachment_router,
    prefix="/api/attachments",
    dependencies=[Depends(get_db)]
)

# 覆盖默认的用户认证依赖
app.dependency_overrides[get_current_user_id] = custom_get_user_id
```

## 📚 API 文档

### 上传文件

```bash
POST /api/attachments/
Content-Type: multipart/form-data

参数:
- file: 文件对象
- is_public: boolean (可选，默认 true)
- description: string (可选)
```

### 获取文件列表

```bash
GET /api/attachments/

查询参数:
- owner_id: int (可选)
- is_public: boolean (可选)
- skip: int (可选，分页偏移)
- limit: int (可选，每页数量)
```

### 获取文件详情

```bash
GET /api/attachments/{attachment_id}/
```

### 下载文件

```bash
GET /api/attachments/{attachment_id}/download/
```

### 删除文件

```bash
DELETE /api/attachments/{attachment_id}/
```

## 🔐 权限模型

- **Public 文件**: 所有人可读，仅所有者可删除
- **Private 文件**: 仅所有者可读可删除
- **Owner ID**: 通过外部认证系统注入，实现认证解耦

## 📁 数据模型

```python
class Attachment:
    id: int
    filename: str          # 原始文件名
    file_path: str         # 物理存储路径
    file_size: int         # 文件大小(字节)
    content_type: str      # MIME 类型
    owner_id: int          # 所有者 ID
    is_public: bool        # 访问级别
    description: str       # 描述信息
    created_at: datetime   # 创建时间
    updated_at: datetime   # 更新时间
```

## 🛠️ 配置选项

### Django 配置

```python
# settings.py

# 文件存储路径
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# 最大上传大小 (可选)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# ChewyAttachment 配置
CHEWY_ATTACHMENT = {
    # 存储根目录
    "STORAGE_ROOT": BASE_DIR / "media" / "attachments",
    # 自定义表名 (可选,默认: "chewy_attachment_files")
    "TABLE_NAME": "my_custom_attachments",
}

# 自定义权限类 (可选)
# 如果不配置,则使用默认权限类
ATTACHMENTS_PERMISSION_CLASSES = [
    "chewy_attachment.django_app.permissions.IsAuthenticatedForUpload",
    "chewy_attachment.django_app.permissions.IsOwnerOrPublicReadOnly",
    # 或使用你的自定义权限类:
    # "myapp.permissions.CustomAttachmentPermission",
]
```

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
ATTACHMENTS_PERMISSION_CLASSES = [
    "chewy_attachment.django_app.permissions.IsAuthenticatedForUpload",
    "myapp.permissions.CustomAttachmentPermission",
]
```

### FastAPI 配置

```python
import os
from chewy_attachment.core.storage import FileStorage

# 自定义存储路径
storage = FileStorage(base_path="/custom/path/media")

# 自定义表名 (通过环境变量)
os.environ["CHEWY_ATTACHMENT_TABLE_NAME"] = "my_custom_attachments"

# 或者在启动应用前设置
# export CHEWY_ATTACHMENT_TABLE_NAME=my_custom_attachments
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
pip install pytest pytest-django pytest-asyncio

# 运行 Django 测试
pytest chewy_attachment/django_app/tests/

# 运行 FastAPI 测试
pytest chewy_attachment/fastapi_app/tests/
```

## 📝 示例代码

查看 `examples/` 目录获取完整的示例项目：

- [Django 示例](examples/django_example/)
- [FastAPI 示例](examples/fastapi_example/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 👤 作者

- GitHub: [@cone387](https://github.com/cone387)

## 🔗 相关链接

- [项目主页](https://github.com/cone387/ChewyAttachment)
- [问题反馈](https://github.com/cone387/ChewyAttachment/issues)
