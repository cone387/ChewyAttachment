# ChewyAttachment v0.5.0 — 需求文档

## 1. 项目概述

ChewyAttachment 是一个通用的文件/附件管理插件，同时支持 Django 和 FastAPI 双框架。提供开箱即用的文件上传、下载、删除、预览功能，支持本地文件存储和 AWS S3 云存储（含 S3 兼容服务），适合个人自托管场景，可被多个业务系统复用。

## 2. 功能需求

### 2.1 文件操作
- REQ-1: 文件上传（支持 multipart/form-data）
- REQ-2: 文件下载（attachment 模式）
- REQ-3: 文件预览（inline 模式，浏览器内显示）
- REQ-4: 文件删除（同时删除存储和数据库记录）
- REQ-5: 文件列表查询（分页、按用户权限过滤）
- REQ-6: 文件元信息查询

### 2.2 存储引擎
- REQ-7: 本地文件存储（FileStorageEngine），按日期分层 `YYYY/MM/DD/<uuid>.<ext>`
- REQ-8: Django 存储后端集成（DjangoStorageEngine），兼容 django-storages
- REQ-9: S3 直连存储（S3StorageEngine），支持 AWS S3、MinIO、阿里云 OSS 等
- REQ-10: 多 S3 配置支持（StorageManager），不同附件可使用不同存储配置
- REQ-11: 存储配置提供者模式（StorageConfigProvider），由接入方安全管理凭证
- REQ-12: 文件迁移（StorageMigrator），支持在不同存储配置之间迁移文件

### 2.3 权限控制
- REQ-13: 基于 owner_id 的权限模型
- REQ-14: public/private 访问级别（public 文件所有人可读，private 仅 owner 可读）
- REQ-15: 仅 owner 可删除文件
- REQ-16: 认证解耦 — Django 从 request.user 获取，FastAPI 通过 dependency 注入

### 2.4 运维接口
- REQ-17: 健康检查接口（/health/），检测数据库和存储引擎状态
- REQ-18: 存储统计接口（/stats/），按用户/全局统计文件数量和大小

### 2.5 框架集成
- REQ-19: Django 集成 — DRF ViewSet、模型交换（类似 AUTH_USER_MODEL）、Admin 界面
- REQ-20: FastAPI 集成 — APIRouter、SQLModel、依赖注入
- REQ-21: 自定义权限类支持（Django DRF permission classes）

### 2.6 文件验证
- REQ-22: 文件大小限制（MAX_FILE_SIZE 配置）
- REQ-23: 文件类型白名单（ALLOWED_EXTENSIONS 配置）
- REQ-24: MIME 类型检测（python-magic 优先，回退到文件名推断）
- REQ-25: 文件名安全处理（Unicode NFC 规范化、控制字符过滤、路径遍历防护）

## 3. 非功能需求

- NFR-1: Python 3.9+ 兼容
- NFR-2: Django 4.2+ / FastAPI 0.109+ 兼容
- NFR-3: 核心包轻量，S3 依赖仅在需要时安装（optional dependencies）
- NFR-4: 线程安全的存储引擎缓存（StorageManager 使用 Lock）
- NFR-5: 云存储文件下载通过 URL 重定向（302），不经过应用服务器
- NFR-6: 签名 URL 支持过期时间配置

## 4. API 端点

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

## 5. 数据模型

```
Attachment:
  id: UUID (PK)
  original_name: VARCHAR(255)
  storage_path: VARCHAR(500)
  mime_type: VARCHAR(100)
  size: BIGINT
  owner_id: VARCHAR(100) [索引]
  is_public: BOOLEAN [索引]
  storage_config_id: VARCHAR(100) [索引, 可空]
  created_at: TIMESTAMP [索引]
```
