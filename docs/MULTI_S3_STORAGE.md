# 多 S3 存储配置指南

ChewyAttachment 支持用户自定义 S3 存储配置，允许不同的附件存储到不同的 S3 服务。

## 核心概念

### 设计原则

1. **配置提供者模式**：ChewyAttachment 不存储敏感的 S3 认证信息，而是通过 `StorageConfigProvider` 接口由接入方提供配置
2. **每个附件记录存储配置**：`Attachment` 模型包含 `storage_config_id` 字段，记录文件存储在哪个 S3 配置
3. **向后兼容**：`storage_config_id` 为可选字段，为空时使用本地存储或系统默认配置

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     接入方应用                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MyStorageConfigProvider                             │   │
│  │  - 管理 S3 配置（加密存储）                           │   │
│  │  - 实现 get_config() / get_default_config()          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ChewyAttachment                           │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │ StorageConfig   │    │ StorageManager              │    │
│  │ Provider (ABC)  │◄───│ - 调用 Provider 获取配置     │    │
│  └─────────────────┘    │ - 创建 S3StorageEngine      │    │
│                         └─────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ EnvironmentStorageConfigProvider (内置默认实现)      │   │
│  │ - 从环境变量读取配置                                 │   │
│  │ - 用于测试和简单场景                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 使用环境变量（测试/简单场景）

最简单的方式是使用内置的 `EnvironmentStorageConfigProvider`，通过环境变量配置 S3：

```bash
# 设置环境变量
export CHEWY_S3_BUCKET_NAME=my-bucket
export CHEWY_S3_ACCESS_KEY=your-access-key
export CHEWY_S3_SECRET_KEY=your-secret-key
export CHEWY_S3_REGION=us-east-1

# 可选：自定义端点（用于 MinIO 等）
export CHEWY_S3_ENDPOINT_URL=http://localhost:9000
export CHEWY_S3_PREFIX=attachments
export CHEWY_S3_PUBLIC_READ=false
```

### 2. 使用 MinIO 本地测试

```bash
# 启动 MinIO
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin123 \
  minio/minio server /data --console-address ":9001"

# 设置环境变量
export CHEWY_S3_ENDPOINT_URL=http://localhost:9000
export CHEWY_S3_BUCKET_NAME=test-attachments
export CHEWY_S3_ACCESS_KEY=minioadmin
export CHEWY_S3_SECRET_KEY=minioadmin123
```

## 自定义配置提供者

对于生产环境，建议实现自定义的 `StorageConfigProvider`：

### Django 示例

```python
# myapp/storage_provider.py
from chewy_attachment.core.storage import StorageConfigProvider
from chewy_attachment.core.schemas import S3ConfigSchema
from chewy_attachment.core.exceptions import StorageException

from myapp.models import S3Config  # 你的 S3 配置模型
from myapp.utils import decrypt  # 你的解密函数


class MyStorageConfigProvider(StorageConfigProvider):
    """从数据库读取 S3 配置"""
    
    def get_config(self, config_id: str) -> S3ConfigSchema:
        try:
            config = S3Config.objects.get(id=config_id, is_active=True)
        except S3Config.DoesNotExist:
            raise StorageException(f"Storage configuration '{config_id}' not found")
        
        return S3ConfigSchema(
            config_id=str(config.id),
            bucket_name=config.bucket_name,
            access_key=decrypt(config.access_key),  # 解密敏感信息
            secret_key=decrypt(config.secret_key),
            region=config.region,
            endpoint_url=config.endpoint_url,
            prefix=config.prefix or "attachments",
            public_read=config.public_read,
        )
    
    def get_default_config(self) -> S3ConfigSchema:
        """获取默认配置"""
        try:
            config = S3Config.objects.get(is_default=True, is_active=True)
            return self.get_config(str(config.id))
        except S3Config.DoesNotExist:
            return None  # 没有默认配置，将使用本地存储
    
    def list_configs(self) -> list:
        """列出所有可用配置"""
        return list(S3Config.objects.filter(is_active=True).values_list('id', flat=True))
```

### 注册配置提供者

```python
# settings.py
CHEWY_ATTACHMENT = {
    'STORAGE_ENGINE': 'file',  # 本地存储作为后备
    'STORAGE_ROOT': BASE_DIR / 'media' / 'attachments',
    'STORAGE_CONFIG_PROVIDER': 'myapp.storage_provider.MyStorageConfigProvider',
}
```

### FastAPI 示例

```python
# main.py
from chewy_attachment.fastapi_app.dependencies import configure
from chewy_attachment.core.storage import StorageConfigProvider
from chewy_attachment.core.schemas import S3ConfigSchema


class MyStorageConfigProvider(StorageConfigProvider):
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    def get_config(self, config_id: str) -> S3ConfigSchema:
        with self.db_session_factory() as session:
            config = session.query(S3ConfigModel).filter_by(id=config_id).first()
            if not config:
                raise StorageException(f"Configuration '{config_id}' not found")
            
            return S3ConfigSchema(
                config_id=config.id,
                bucket_name=config.bucket_name,
                access_key=decrypt(config.access_key),
                secret_key=decrypt(config.secret_key),
                region=config.region,
                endpoint_url=config.endpoint_url,
            )
    
    def get_default_config(self) -> S3ConfigSchema:
        with self.db_session_factory() as session:
            config = session.query(S3ConfigModel).filter_by(is_default=True).first()
            if config:
                return self.get_config(config.id)
            return None


# 配置应用
provider = MyStorageConfigProvider(get_db_session)
configure(
    database_url="sqlite:///./attachments.db",
    storage_root="./media/attachments",
    storage_config_provider=provider,
)
```

## API 使用

### 上传文件时指定存储配置

```bash
# 使用默认存储配置
curl -X POST http://localhost:8000/api/attachments/files/ \
  -H "Authorization: Bearer your-token" \
  -F "file=@example.jpg" \
  -F "is_public=false"

# 指定特定的存储配置
curl -X POST http://localhost:8000/api/attachments/files/ \
  -H "Authorization: Bearer your-token" \
  -F "file=@example.jpg" \
  -F "is_public=false" \
  -F "storage_config_id=my-custom-s3-config"
```

### 响应示例

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_name": "example.jpg",
  "mime_type": "image/jpeg",
  "size": 102400,
  "owner_id": "123",
  "is_public": false,
  "storage_config_id": "my-custom-s3-config",
  "created_at": "2026-02-05 17:00:00",
  "preview_url": "/api/attachments/files/550e8400.../preview/",
  "download_url": "/api/attachments/files/550e8400.../content/"
}
```

## 用户切换存储配置

当用户切换默认存储配置时：

- **旧文件**：`storage_config_id` 指向旧配置，仍能正常访问
- **新文件**：使用新的 `storage_config_id`
- **无需迁移数据**

### 可选：数据迁移

如果需要将旧数据迁移到新存储，可以实现迁移脚本：

```python
from chewy_attachment.core.storage import StorageManager

def migrate_attachments(attachment_ids, target_config_id):
    """将附件迁移到新的存储配置"""
    manager = StorageManager.get_instance()
    
    for attachment in Attachment.objects.filter(id__in=attachment_ids):
        # 从旧存储读取
        old_storage = manager.get_engine(attachment.storage_config_id)
        content = old_storage.get_file(attachment.storage_path)
        
        # 写入新存储
        new_storage = manager.get_engine(target_config_id)
        result = new_storage.save_file(content, attachment.original_name)
        
        # 更新记录
        old_path = attachment.storage_path
        attachment.storage_path = result.storage_path
        attachment.storage_config_id = target_config_id
        attachment.save()
        
        # 可选：删除旧文件
        old_storage.delete_file(old_path)
```

## S3ConfigSchema 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `config_id` | str | 是 | 配置唯一标识 |
| `bucket_name` | str | 是 | S3 存储桶名称 |
| `access_key` | str | 是 | AWS Access Key ID |
| `secret_key` | str | 是 | AWS Secret Access Key |
| `region` | str | 否 | AWS 区域，默认 `us-east-1` |
| `endpoint_url` | str | 否 | 自定义 S3 端点（用于 MinIO 等） |
| `prefix` | str | 否 | 文件路径前缀，默认 `attachments` |
| `public_read` | bool | 否 | 是否公开可读，默认 `False` |
| `extra_options` | dict | 否 | 额外配置选项 |

## 安全建议

1. **加密存储敏感信息**：`access_key` 和 `secret_key` 应加密存储在数据库中
2. **使用环境变量**：生产环境中，敏感信息应通过环境变量或密钥管理服务获取
3. **最小权限原则**：为每个 S3 配置创建专用的 IAM 用户，仅授予必要权限
4. **审计日志**：如需追踪配置变更，在 `StorageConfigProvider` 中实现日志记录
