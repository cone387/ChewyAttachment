# ChewyAttachment v0.5.0 — 技术设计文档

## 1. 架构概览

```
chewy_attachment/
├── core/                          # 框架无关的核心层
│   ├── exceptions.py              # 异常层次: ChewyAttachmentException → 子类
│   ├── schemas.py                 # 数据结构: FileMetadata, UserContext, S3ConfigSchema, ...
│   ├── permissions.py             # 权限检查: PermissionChecker (静态方法)
│   ├── storage.py                 # 存储引擎: BaseStorageEngine → File/Django/S3
│   │                              #           StorageConfigProvider (ABC)
│   │                              #           StorageManager (单例, 多S3管理)
│   │                              #           StorageMigrator (跨存储迁移)
│   └── utils.py                   # 工具: UUID, MIME检测, 文件名安全处理
│
├── django_app/                    # Django 实现层
│   ├── models.py                  # AttachmentBase (abstract) + Attachment (swappable)
│   ├── views.py                   # AttachmentViewSet + HealthCheckView + StorageStatsView
│   ├── serializers.py             # AttachmentSerializer + AttachmentUploadSerializer
│   ├── storage.py                 # Django 存储配置工具
│   ├── permissions.py             # DRF 权限类
│   ├── admin.py                   # Django Admin (文件预览、批量操作)
│   └── urls.py                    # URL 路由
│
└── fastapi_app/                   # FastAPI 实现层
    ├── models.py                  # SQLModel Attachment
    ├── router.py                  # APIRouter (files + health + stats)
    ├── schemas.py                 # Pydantic 响应模型
    ├── crud.py                    # CRUD 操作
    └── dependencies.py            # 依赖注入 (DB, Storage, Auth, Permissions)
```

## 2. 存储引擎架构

### 2.1 类层次

```
BaseStorageEngine (ABC)
├── FileStorageEngine          # 本地文件系统
├── DjangoStorageEngine        # Django storage backend (django-storages)
└── S3StorageEngine            # 直连 S3 (boto3)
    └── from_config(cls)       # 从 S3ConfigSchema 创建实例

StorageConfigProvider (ABC)
├── EnvironmentStorageConfigProvider  # 从环境变量读取 (内置默认)
└── 用户自定义 Provider               # 从数据库/配置中心读取

StorageManager (单例)
├── get_engine(config_id)             # 按 ID 获取引擎 (带缓存)
├── get_default_engine()              # 获取默认引擎 (S3 优先, 本地回退)
└── get_engine_for_attachment(id?)    # 返回 (engine, config_id) 元组

StorageMigrator
├── migrate_file(attachment, target_config_id)
└── migrate_batch(attachments, target_config_id, callback?)
```

### 2.2 存储路径策略

所有引擎共用 `_generate_storage_path()`:
```
YYYY/MM/DD/<uuid>.<ext>
```

S3 引擎额外加 prefix: `<prefix>/YYYY/MM/DD/<uuid>.<ext>`

### 2.3 云存储文件服务策略

- **本地存储**: 直接通过应用服务器流式传输文件
- **S3/云存储**: 生成签名 URL，返回 302 重定向，不经过应用服务器
- **判断逻辑**: `_is_cloud_storage()` 检查引擎类型

## 3. Django 集成设计

### 3.1 模型交换

类似 `AUTH_USER_MODEL` 机制:
```python
# settings.py
CHEWY_ATTACHMENT_MODEL = 'myapp.MyAttachment'
```

`get_attachment_model()` 动态解析模型类。

### 3.2 存储配置

#[[file:chewy_attachment/django_app/storage.py]] 提供:
- `get_storage_engine()` — 根据 `CHEWY_ATTACHMENT["STORAGE_ENGINE"]` 返回引擎
- `get_storage_engine_for_attachment(config_id)` — 多 S3 场景
- `get_storage_engine_for_upload(config_id)` — 上传时确定存储目标

### 3.3 配置项

```python
CHEWY_ATTACHMENT = {
    "STORAGE_ENGINE": "file" | "django",     # 存储引擎类型
    "STORAGE_ROOT": Path,                     # 本地存储路径
    "DJANGO_STORAGE_CLASS": str,              # 自定义 Django 存储类
    "MAX_FILE_SIZE": int,                     # 文件大小限制 (bytes)
    "ALLOWED_EXTENSIONS": list[str],          # 允许的扩展名
    "PERMISSION_CLASSES": list[str],          # DRF 权限类
    "DATETIME_FORMAT": str,                   # 时间格式
    "STORAGE_CONFIG_PROVIDER": str,           # 多 S3 配置提供者类路径
}
```

## 4. FastAPI 集成设计

### 4.1 初始化

```python
from chewy_attachment.fastapi_app.dependencies import configure

configure(
    database_url="sqlite:///./app.db",
    storage_root="./media/attachments",
    storage_config_provider=MyProvider(),  # 可选
)
```

### 4.2 依赖注入链

```
get_session() → Session
get_storage_engine() → BaseStorageEngine
get_current_user() → UserContext (可被 override)
get_current_user_required() → UserContext (401 if anonymous)
require_view_permission() → Attachment (403 if denied)
require_delete_permission() → Attachment (403 if denied)
```

## 5. 权限模型

```
PermissionChecker:
  can_view(file, user)     → is_public OR owner
  can_download(file, user) → same as can_view
  can_delete(file, user)   → owner only
```

Django 额外支持自定义 DRF permission classes。

## 6. 安全设计

- **路径遍历防护**: `_get_full_path()` 使用 `resolve()` + 前缀检查
- **文件名安全**: Unicode NFC 规范化 + 控制字符过滤 + 仅保留 basename
- **MIME 检测**: python-magic 基于文件内容检测，不依赖扩展名
- **S3 凭证**: 不存储在 ChewyAttachment 中，通过 Provider 模式由接入方管理
- **签名 URL**: 私有文件通过带过期时间的签名 URL 访问

## 7. 关键文件引用

- #[[file:chewy_attachment/core/storage.py]] — 存储引擎核心
- #[[file:chewy_attachment/core/schemas.py]] — 数据结构定义
- #[[file:chewy_attachment/core/permissions.py]] — 权限逻辑
- #[[file:chewy_attachment/django_app/views.py]] — Django API 视图
- #[[file:chewy_attachment/django_app/models.py]] — Django 数据模型
- #[[file:chewy_attachment/django_app/storage.py]] — Django 存储配置
- #[[file:chewy_attachment/fastapi_app/router.py]] — FastAPI 路由
- #[[file:chewy_attachment/fastapi_app/dependencies.py]] — FastAPI 依赖注入
- #[[file:pyproject.toml]] — 项目配置和依赖
