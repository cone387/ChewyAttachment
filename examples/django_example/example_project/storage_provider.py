"""
多 S3 存储配置提供者示例

配置两个独立的 MinIO 实例：
- MinIO 1 (s3-primary): localhost:9000
- MinIO 2 (s3-secondary): localhost:9002
"""

from chewy_attachment.core.storage import StorageConfigProvider
from chewy_attachment.core.schemas import S3ConfigSchema
from chewy_attachment.core.exceptions import StorageException


class DualMinioProvider(StorageConfigProvider):
    """
    双 MinIO 存储配置提供者
    
    在实际项目中，这些配置通常从数据库或配置中心读取
    """
    
    def __init__(self):
        self._configs = {
            "s3-primary": S3ConfigSchema(
                config_id="s3-primary",
                bucket_name="bucket-s3-1",
                access_key="minioadmin",
                secret_key="minioadmin123",
                endpoint_url="http://localhost:9000",
                prefix="primary-storage",
            ),
            "s3-secondary": S3ConfigSchema(
                config_id="s3-secondary",
                bucket_name="bucket-s3-2",
                access_key="minioadmin2",
                secret_key="minioadmin456",
                endpoint_url="http://localhost:9002",
                prefix="secondary-storage",
            ),
        }
    
    def get_config(self, config_id: str) -> S3ConfigSchema:
        """获取指定 ID 的存储配置"""
        if config_id not in self._configs:
            raise StorageException(f"Storage config '{config_id}' not found")
        return self._configs[config_id]
    
    def get_default_config(self) -> S3ConfigSchema:
        """获取默认存储配置"""
        return self._configs["s3-primary"]
    
    def list_configs(self) -> list:
        """列出所有可用的配置 ID"""
        return list(self._configs.keys())
