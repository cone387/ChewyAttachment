# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/cone387/ChewyAttachment/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cone387/ChewyAttachment/releases/tag/v0.1.0
