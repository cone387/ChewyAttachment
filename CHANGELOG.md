# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.2] - 2026-04-15

### Fixed
- **CRITICAL**: FastAPI `create_attachment()` did not persist `storage_config_id` — files uploaded to S3 lost their storage config, causing 404 on download
- **MEDIUM**: `S3StorageEngine.get_file_url()` produced malformed URLs for custom endpoints (MinIO) — accessed boto3 private attributes, now stores endpoint_url/region_name directly
- **MEDIUM**: Django admin preview URLs were hardcoded `/api/attachments/...` — now uses `reverse()` with fallback
- **MEDIUM**: `file_url` in API response returned raw storage path (`2026/04/15/uuid.txt`) for local storage instead of a usable download URL
- FastAPI example missing `health_router` mount — health/stats endpoints returned 404
- Django S3 example `settings.py` in wrong directory — demo couldn't start
- Django basic example had unnecessary MinIO `STORAGE_CONFIG_PROVIDER` config
- `__init__.py` fallback version was stale

### Added
- 32 new tests (108 total): health check, stats, preview, pagination, edge cases, StorageManager
- End-to-end validation: 22 tests across Django (12) and FastAPI (10) examples
- GitHub Actions CI/CD workflows (lint + test matrix + PyPI publish)

### Changed
- `AttachmentSerializer.get_file_url()` now returns `download_url` for local storage, direct/signed URL only for cloud storage

## [0.5.1] - 2026-04-15

### Fixed
- Remove redundant `file_exists()` call in `DjangoStorageEngine.get_file_url()` — eliminates extra S3 HEAD request per URL generation
- Remove redundant `file_exists()` call in `S3StorageEngine.get_file_url()` — signed URLs have their own expiry, no need to pre-check
- Add `le=10000` upper bound to FastAPI `page` query parameter — prevents extreme offset queries

### Added
- **MIME content validation** (`VALIDATE_MIME_CONTENT` setting) — detects executable content disguised as safe file types (e.g. ELF binary renamed to .jpg)
- **GitHub Actions CI/CD** — lint + test matrix (Python 3.10-3.13) on push/PR, auto-publish to PyPI on tag
- New test suite for serializer validation (6 tests)
- FastAPI pagination boundary tests (3 tests) and preview endpoint test

### Changed
- Total test count: 75 (up from 65)

## [0.5.0] - 2026-01-21

### Added
- **AWS S3 云存储支持** 🎉
  - 通过 django-storages 集成 AWS S3 和兼容 S3 的云存储服务
  - 新增 `django-s3` 和 `fastapi-s3` 安装选项
  - 支持私有文件的签名 URL 访问
  - 支持公有文件的直接 URL 访问
- **存储引擎架构重构**
  - 新增 `DjangoStorageEngine` 类，完全兼容 django-storages
  - 保留现有的 `FileStorageEngine` 用于本地存储
  - 新增 `S3StorageEngine` 用于 FastAPI 直接 S3 集成
- **配置系统增强**
  - 新增 `STORAGE_ENGINE` 配置选项 (`"file"` 或 `"django"`)
  - 新增 `chewy_attachment.django_app.storage` 模块提供存储配置工具
  - 支持自定义 S3 存储类配置
- **文件验证功能**
  - 新增 `MAX_FILE_SIZE` 配置选项
  - 新增 `ALLOWED_EXTENSIONS` 配置选项
  - 序列化器自动验证文件大小和类型
- **API 响应增强**
  - 新增 `download_url` 字段
  - 新增 `file_url` 字段（云存储直接访问 URL）
  - 改进文件下载和预览的 URL 重定向逻辑
- **管理命令**
  - 新增 `test_s3_storage` 管理命令用于测试 S3 配置
  - 支持 `--cleanup` 参数自动清理测试文件
- **完整文档**
  - 新增 `docs/S3_STORAGE.md` 详细配置指南
  - 新增 Django S3 示例项目 `examples/django_s3_example/`
  - 更新 README 添加 S3 配置说明

### Changed
- **视图逻辑优化**
  - 文件下载和预览支持云存储 URL 重定向
  - 改进存储引擎获取逻辑，统一使用 `get_storage_engine()` 函数
- **依赖管理**
  - `boto3` 添加到 `django-s3` 和 `fastapi-s3` 依赖组
  - 保持核心包轻量，S3 依赖仅在需要时安装

### Technical Details
- 完全向后兼容，现有本地存储配置无需修改
- S3 存储支持 MinIO、阿里云 OSS 等 S3 兼容服务
- 支持 CloudFront CDN 集成
- 自动处理签名 URL 生成和过期时间
- 支持多区域 S3 配置

## [0.4.3] - 2026-01-20

### Fixed
- Refactored duplicate `get_attachment_model()` methods in ViewSets
- Extracted model resolution logic to module-level function to follow DRY principle
- Improved code maintainability by eliminating redundant implementations

### Changed
- `get_attachment_model()` is now a module-level function instead of class methods
- All ViewSets use the same model resolution logic consistently

## [0.4.2] - 2026-01-20

### Fixed
- Fixed Django app label configuration issue
- Added explicit `label = "chewy_attachment_django_app"` in AppConfig to avoid conflicts
- Corrected `apps.get_model()` calls to use proper app label instead of module path
- Removed unnecessary `requests` dependency from core dependencies
- Regenerated clean migration files with correct app label references

### Changed
- Django app now uses explicit app label `chewy_attachment_django_app` instead of auto-generated `django_app`
- Cleaned up dependencies: `requests` moved out of core dependencies (was only needed for testing)
- Migration files regenerated for consistency and proper app label usage

### Tested
- All 12 Django unit tests passing
- Complete API functionality verified (upload, download, delete, permissions)
- Anonymous and authenticated user access patterns validated

## [0.4.1] - 2026-01-20

### Fixed
- Fixed Django model swapping compatibility issue in ViewSets
- ViewSets now properly use `apps.get_model()` to support swapped models
- Resolved "Manager isn't available" error when using `CHEWY_ATTACHMENT_MODEL` setting

### Changed
- ViewSets no longer use hardcoded `queryset` attribute, instead dynamically resolve models
- Added `get_attachment_model()` method to ViewSets for consistent model access

## [0.4.0] - 2026-01-20

### Added
- Django swappable model support (similar to `AUTH_USER_MODEL`)
- `CHEWY_ATTACHMENT_MODEL` setting for custom model configuration
- Abstract base class `AttachmentBase` for easy model inheritance

### Changed
- **BREAKING**: Default table name changed from `chewy_attachment_files` to `chewy_attachments`
- **BREAKING**: Removed `TABLE_NAME` configuration option in favor of swappable models
- Simplified architecture by removing unnecessary utility functions
- Updated documentation to focus on swappable model approach

### Removed
- `utils.py` module (no longer needed with swappable models)
- Dynamic table name configuration via settings

### Migration Guide
For existing users upgrading from v0.3.x:
1. The default table name has changed. If you want to keep your existing data:
   - Create a custom model inheriting from `AttachmentBase`
   - Set `db_table = "chewy_attachment_files"` in your model's Meta class
   - Configure `CHEWY_ATTACHMENT_MODEL` in settings
2. Or migrate your data to the new table name `chewy_attachments`

## [0.2.0] - 2026-01-13

### Added
- Support for custom permission classes via `ATTACHMENTS_PERMISSION_CLASSES` setting (Django)
- Support for custom table name configuration:
  - Django: Configure via `CHEWY_ATTACHMENT['TABLE_NAME']` in settings.py
  - FastAPI: Configure via `CHEWY_ATTACHMENT_TABLE_NAME` environment variable
- Custom permission class example in documentation
- PyPI badges in README

### Changed
- Lower Django version requirement from >=5.0.0 to >=4.2.0 for better compatibility
- Improved documentation with comprehensive configuration examples

### Fixed
- Python version compatibility (now supports Python 3.9+)

## [0.1.0] - 2026-01-13

### Added
- Initial release
- Core features:
  - File upload, download, delete operations
  - Support for both Django and FastAPI frameworks
  - Public/Private access control
  - Owner-based permission model
  - RESTful API design
  - Markdown-friendly file reference links
  - SQLite + local file system storage
- Complete documentation and examples
- Test coverage for Django app
- FastAPI integration examples

[0.4.1]: https://github.com/cone387/ChewyAttachment/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/cone387/ChewyAttachment/compare/v0.3.2...v0.4.0
[0.2.0]: https://github.com/cone387/ChewyAttachment/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cone387/ChewyAttachment/releases/tag/v0.1.0
