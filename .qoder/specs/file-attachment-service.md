# ChewyAttachment - 通用附件管理插件实现计划

## 概述

设计并实现一个通用的图片/附件管理插件，同时支持 Django 和 FastAPI 两大框架，使用 SQLite 存储元数据，本地文件系统存储文件。

## 项目架构

```
ChewyAttachment/
├── pyproject.toml                 # uv 项目配置
├── chewy_attachment/              # 主包
│   ├── __init__.py
│   ├── core/                      # 核心业务逻辑（框架无关）
│   │   ├── __init__.py
│   │   ├── storage.py            # 文件存储引擎
│   │   ├── permissions.py        # 权限校验逻辑
│   │   ├── schemas.py            # 通用数据模型 (dataclass)
│   │   ├── exceptions.py         # 自定义异常
│   │   └── utils.py              # 工具函数
│   │
│   ├── django_app/                # Django 实现
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── conftest.py
│   │       └── test_views.py
│   │
│   └── fastapi_app/               # FastAPI 实现
│       ├── __init__.py
│       ├── models.py
│       ├── schemas.py
│       ├── router.py
│       ├── dependencies.py
│       ├── crud.py
│       └── tests/
│           ├── conftest.py
│           └── test_router.py
│
└── examples/                       # 使用示例
    ├── django_example/
    └── fastapi_example/
```

## 核心设计

### 数据模型

```
表名: chewy_attachment_files

字段:
- id: UUID (Primary Key)
- original_name: VARCHAR(255)
- storage_path: VARCHAR(500)
- mime_type: VARCHAR(100)
- size: BIGINT
- owner_id: VARCHAR(100) [索引]
- is_public: BOOLEAN (默认 False) [索引]
- created_at: TIMESTAMP [索引]
```

### 文件存储策略

```
<STORAGE_ROOT>/YYYY/MM/DD/<UUID>.<ext>
```

按日期分层存储，使用 UUID 作为文件名。

### 用户认证

- **Django**: 仅从 `request.user` 获取当前用户 ID
- **FastAPI**: 仅通过 dependency 注入获取当前用户 ID
- 不支持自定义 Header 方式

### 文件大小限制

- 插件本身不做限制
- 由外部系统（如 Nginx、Web 服务器）控制

### 权限规则

| 操作 | 规则 |
|------|------|
| 查看/下载 | `is_public=True` OR `owner_id == current_user_id` |
| 删除 | `owner_id == current_user_id` |

### API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /files | 上传文件 |
| GET | /files/{id} | 获取文件信息 |
| GET | /files/{id}/content | 下载文件 |
| DELETE | /files/{id} | 删除文件 |

## 实现步骤

### Step 1: 项目初始化
- 创建 `pyproject.toml` 配置 uv 和依赖
- 创建包结构和 `__init__.py` 文件

### Step 2: Core 层实现
- `core/exceptions.py`: 自定义异常类
- `core/schemas.py`: 通用数据结构 (dataclass)
- `core/utils.py`: UUID 生成、MIME 检测
- `core/storage.py`: 文件存储引擎
- `core/permissions.py`: 权限校验逻辑

### Step 3: Django App 实现
- `django_app/apps.py`: Django AppConfig
- `django_app/models.py`: Attachment 模型
- `django_app/serializers.py`: DRF 序列化器
- `django_app/permissions.py`: DRF 权限类
- `django_app/views.py`: ViewSet 和下载视图
- `django_app/urls.py`: URL 路由

### Step 4: FastAPI App 实现
- `fastapi_app/models.py`: SQLModel 模型
- `fastapi_app/schemas.py`: Pydantic Schemas
- `fastapi_app/crud.py`: CRUD 操作
- `fastapi_app/dependencies.py`: 依赖注入
- `fastapi_app/router.py`: APIRouter

### Step 5: 单元测试
- Django 测试 (pytest-django)
- FastAPI 测试 (pytest + TestClient)
- 覆盖场景:
  - 文件上传成功
  - 非 owner 删除 → 403
  - owner 删除成功
  - 私有文件权限校验
  - 公开文件匿名访问

### Step 6: 示例项目
- Django 集成示例
- FastAPI 集成示例

## 依赖包

**核心:**
- python-magic (MIME 检测)

**Django:**
- django>=5.0
- djangorestframework>=3.14

**FastAPI:**
- fastapi>=0.109
- sqlmodel>=0.0.14
- python-multipart

**测试:**
- pytest
- pytest-django
- httpx

## 关键文件

1. `chewy_attachment/core/storage.py` - 文件存储核心逻辑
2. `chewy_attachment/core/permissions.py` - 权限校验核心逻辑
3. `chewy_attachment/django_app/models.py` - Django 数据模型
4. `chewy_attachment/django_app/views.py` - Django API 视图
5. `chewy_attachment/fastapi_app/models.py` - FastAPI 数据模型
6. `chewy_attachment/fastapi_app/router.py` - FastAPI 路由

## 验证方式

1. **Django 测试:**
   ```bash
   cd examples/django_example
   pytest ../chewy_attachment/django_app/tests/ -v
   ```

2. **FastAPI 测试:**
   ```bash
   pytest chewy_attachment/fastapi_app/tests/ -v
   ```

3. **手动测试:**
   - 启动 Django/FastAPI 示例服务
   - 使用 curl 或 Postman 测试 API 端点
