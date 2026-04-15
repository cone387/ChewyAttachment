# ChewyAttachment — 任务清单

## 已完成 ✅

### Phase 1: 核心框架 (v0.1.0)
- [x] Task 1: 项目初始化 — pyproject.toml、包结构、__init__.py
- [x] Task 2: Core 异常体系 — ChewyAttachmentException 及子类
- [x] Task 3: Core 数据结构 — FileMetadata, UserContext, FileUploadResult
- [x] Task 4: Core 工具函数 — UUID 生成、MIME 检测、文件名安全处理
- [x] Task 5: Core 权限检查 — PermissionChecker (view/download/delete)
- [x] Task 6: 本地文件存储引擎 — FileStorageEngine
- [x] Task 7: Django 模型 — AttachmentBase + Attachment
- [x] Task 8: Django 序列化器 — AttachmentSerializer + AttachmentUploadSerializer
- [x] Task 9: Django 视图 — AttachmentViewSet (CRUD + download + preview)
- [x] Task 10: Django 权限类 — IsAuthenticatedForUpload, IsOwnerOrPublicReadOnly
- [x] Task 11: Django URL 路由
- [x] Task 12: FastAPI 模型 — SQLModel Attachment
- [x] Task 13: FastAPI CRUD 操作
- [x] Task 14: FastAPI 依赖注入 — DB, Storage, Auth, Permissions
- [x] Task 15: FastAPI 路由 — 文件 CRUD + download + preview
- [x] Task 16: Django 单元测试 (12 tests)
- [x] Task 17: FastAPI 单元测试 (13 tests)
- [x] Task 18: 示例项目 — Django + FastAPI

### Phase 2: 模型交换 + Admin (v0.4.x)
- [x] Task 19: Django 模型交换机制 — CHEWY_ATTACHMENT_MODEL (类似 AUTH_USER_MODEL)
- [x] Task 20: Django Admin 界面 — 文件预览、类型徽章、批量操作
- [x] Task 21: 自定义权限类加载 — PERMISSION_CLASSES 配置

### Phase 3: S3 云存储 (v0.5.0)
- [x] Task 22: DjangoStorageEngine — 兼容 django-storages
- [x] Task 23: S3StorageEngine — 直连 boto3
- [x] Task 24: S3ConfigSchema 数据结构
- [x] Task 25: StorageConfigProvider 抽象接口
- [x] Task 26: EnvironmentStorageConfigProvider 默认实现
- [x] Task 27: StorageManager 单例 — 多 S3 配置管理、引擎缓存
- [x] Task 28: StorageMigrator — 跨存储文件迁移
- [x] Task 29: Django 存储配置模块 — get_storage_engine() 系列函数
- [x] Task 30: FastAPI 多 S3 支持 — configure() 接受 StorageConfigProvider
- [x] Task 31: 文件验证 — MAX_FILE_SIZE + ALLOWED_EXTENSIONS
- [x] Task 32: API 响应增强 — download_url + file_url 字段
- [x] Task 33: 云存储文件服务 — 302 重定向到签名 URL
- [x] Task 34: 健康检查接口 — /health/ (Django + FastAPI)
- [x] Task 35: 存储统计接口 — /stats/ (Django + FastAPI)
- [x] Task 36: test_s3_storage 管理命令
- [x] Task 37: S3 配置文档 — docs/S3_STORAGE.md
- [x] Task 38: 多 S3 配置文档 — docs/MULTI_S3_STORAGE.md
- [x] Task 39: 测试指南文档 — docs/TESTING.md

### Phase 3.1: 代码质量修复 (v0.5.0 patch)
- [x] Task 40: safe_filename Unicode NFC 规范化 + 控制字符过滤
- [x] Task 41: 删除 AttachmentDownloadView 死代码
- [x] Task 42: DRY download/preview → _serve_file() + _is_cloud_storage()
- [x] Task 43: Admin 使用统一存储引擎 (不再硬编码 FileStorageEngine)
- [x] Task 44: 添加 logging 到 Django views
- [x] Task 45: 修复 FastAPI 测试 conftest 缺少 StorageManager 配置

## 待办 📋

### Phase 4: 质量提升 (v0.5.1)
- [x] Task 46: DjangoStorageEngine.get_file_url() 去掉多余的 file_exists() 调用
- [x] Task 47: S3StorageEngine.get_file_url() 去掉多余的 file_exists() 调用
- [x] Task 48: FastAPI page 参数加上限 (le=10000)
- [x] Task 49: 文件内容 MIME 校验 — VALIDATE_MIME_CONTENT 配置项
- [x] Task 50: GitHub Actions CI/CD — lint + test + publish
- [x] Task 51: 补充 serializer 验证测试 (6 tests)
- [x] Task 52: 补充 FastAPI 分页边界和 preview 测试 (4 tests)

### Phase 5: 功能增强 (v0.6.0)
- [ ] Task 53: 补充核心模块单元测试 — StorageManager, StorageMigrator, S3StorageEngine
- [ ] Task 54: 补充安全测试 — 路径遍历、恶意文件名、权限绕过
- [ ] Task 55: 批量上传/删除接口
- [ ] Task 56: 文件去重 — 基于内容哈希
- [ ] Task 57: 异步文件操作 — Django async views
- [ ] Task 58: 缩略图生成 — 图片自动生成缩略图
- [ ] Task 59: Webhook 通知 — 文件上传/删除事件回调
- [ ] Task 60: 速率限制 — 上传/下载频率控制
