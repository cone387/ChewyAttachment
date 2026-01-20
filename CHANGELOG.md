# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.4.0]: https://github.com/cone387/ChewyAttachment/compare/v0.3.2...v0.4.0
[0.2.0]: https://github.com/cone387/ChewyAttachment/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cone387/ChewyAttachment/releases/tag/v0.1.0
