# S3 存储配置指南

ChewyAttachment 支持通过 django-storages 使用 AWS S3 和兼容 S3 的云存储服务。

## 安装依赖

```bash
# 安装 S3 支持
pip install 'chewy-attachment[django-s3]'

# 或者手动安装依赖
pip install django-storages[s3] boto3
```

## 基础配置

### 1. 添加到 INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... 其他应用
    'storages',  # django-storages
    'chewy_attachment.django_app',
]
```

### 2. AWS S3 配置

```python
# settings.py

# AWS 凭证 (推荐使用环境变量或 IAM 角色)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'your-bucket-name')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# S3 设置
AWS_S3_CUSTOM_DOMAIN = None  # 如果使用 CloudFront，设置域名
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # 1天缓存
}

# 文件存储设置
AWS_DEFAULT_ACL = 'private'  # 文件默认私有
AWS_S3_FILE_OVERWRITE = False  # 不覆盖同名文件
AWS_QUERYSTRING_AUTH = True  # 使用签名 URL
AWS_QUERYSTRING_EXPIRE = 3600  # 签名 URL 1小时过期

# 使用 S3 作为媒体文件存储
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 媒体文件 URL
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
else:
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'
```

### 3. ChewyAttachment 配置

```python
# settings.py

CHEWY_ATTACHMENT = {
    # 使用 Django 存储系统 (已配置为 S3)
    'STORAGE_ENGINE': 'django',
    
    # 文件大小限制
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    
    # 允许的文件类型
    'ALLOWED_EXTENSIONS': [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        '.pdf', '.doc', '.docx', '.txt', '.zip',
    ],
    
    # 权限设置
    'DEFAULT_PERMISSION': 'private',
    'ALLOW_ANONYMOUS_UPLOAD': False,
    'ALLOW_ANONYMOUS_ACCESS': False,
    
    # URL 设置
    'URL_EXPIRES_IN': 3600,  # 签名 URL 1小时过期
}
```

## 高级配置

### 自定义存储类

如果需要更多控制，可以创建自定义存储类：

```python
# storage.py
from storages.backends.s3boto3 import S3Boto3Storage

class MediaStorage(S3Boto3Storage):
    bucket_name = 'your-bucket-name'
    location = 'media'  # 存储在 media 文件夹
    default_acl = 'private'
    file_overwrite = False
    custom_domain = None  # 或者你的 CloudFront 域名

# settings.py
CHEWY_ATTACHMENT = {
    'STORAGE_ENGINE': 'django',
    'DJANGO_STORAGE_CLASS': 'myapp.storage.MediaStorage',
    # ... 其他设置
}
```

### 分离静态文件和媒体文件

```python
# settings.py

# 静态文件使用 S3
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
AWS_STATIC_LOCATION = 'static'

# 媒体文件使用 S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_MEDIA_LOCATION = 'media'

# 或者使用自定义存储类
class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'

class MediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'private'
    file_overwrite = False
```

### 使用 CloudFront CDN

```python
# settings.py

# CloudFront 配置
AWS_S3_CUSTOM_DOMAIN = 'your-cloudfront-domain.cloudfront.net'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# 媒体文件 URL 将使用 CloudFront
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
```

## 环境变量配置

创建 `.env` 文件：

```bash
# .env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=your-cloudfront-domain.cloudfront.net
```

在 settings.py 中加载：

```python
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# ... 其他配置
```

## S3 兼容服务

### MinIO

```python
# settings.py

# MinIO 配置
AWS_ACCESS_KEY_ID = 'your-minio-access-key'
AWS_SECRET_ACCESS_KEY = 'your-minio-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket'
AWS_S3_ENDPOINT_URL = 'http://localhost:9000'  # MinIO 端点
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_USE_SSL = False  # 如果使用 HTTP
```

### 阿里云 OSS

```python
# settings.py

# 阿里云 OSS (使用 S3 兼容接口)
AWS_ACCESS_KEY_ID = 'your-oss-access-key'
AWS_SECRET_ACCESS_KEY = 'your-oss-secret-key'
AWS_STORAGE_BUCKET_NAME = 'your-bucket'
AWS_S3_ENDPOINT_URL = 'https://oss-cn-hangzhou.aliyuncs.com'
AWS_S3_REGION_NAME = 'cn-hangzhou'
```

## 测试配置

使用管理命令测试 S3 配置：

```bash
# 测试 S3 连接和基本操作
python manage.py test_s3_storage

# 测试并清理测试文件
python manage.py test_s3_storage --cleanup

# 使用自定义测试文件
python manage.py test_s3_storage --test-file my-test.jpg --cleanup
```

## 权限配置

### S3 存储桶策略

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowAppAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:user/your-app-user"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### IAM 用户策略

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetObjectAcl",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

## 常见问题

### 1. 签名 URL 不工作

确保设置了正确的权限：

```python
AWS_QUERYSTRING_AUTH = True
AWS_DEFAULT_ACL = 'private'
```

### 2. 文件上传慢

考虑使用 CloudFront 或启用传输加速：

```python
AWS_S3_TRANSFER_CONFIG = {
    'multipart_threshold': 1024 * 25,  # 25MB
    'max_concurrency': 10,
    'multipart_chunksize': 1024 * 25,
    'use_threads': True
}
```

### 3. CORS 问题

在 S3 存储桶中配置 CORS：

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "POST", "PUT", "DELETE"],
        "AllowedOrigins": ["https://yourdomain.com"],
        "ExposeHeaders": []
    }
]
```

### 4. 成本优化

使用生命周期策略自动删除旧文件：

```json
{
    "Rules": [
        {
            "ID": "DeleteOldFiles",
            "Status": "Enabled",
            "Filter": {"Prefix": "attachments/"},
            "Expiration": {"Days": 365}
        }
    ]
}
```

## 迁移现有文件

如果需要从本地存储迁移到 S3：

```python
# management/commands/migrate_to_s3.py
from django.core.management.base import BaseCommand
from chewy_attachment.django_app.models import Attachment
from chewy_attachment.django_app.storage import get_storage_engine

class Command(BaseCommand):
    def handle(self, *args, **options):
        old_storage = FileStorageEngine('/path/to/old/files')
        new_storage = get_storage_engine()  # S3 storage
        
        for attachment in Attachment.objects.all():
            # 读取旧文件
            content = old_storage.get_file(attachment.storage_path)
            
            # 保存到新存储
            result = new_storage.save_file(content, attachment.original_name)
            
            # 更新数据库记录
            attachment.storage_path = result.storage_path
            attachment.save()
            
            self.stdout.write(f'Migrated: {attachment.original_name}')
```

## 监控和日志

启用 S3 访问日志：

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'storage.log',
        },
    },
    'loggers': {
        'storages': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

这样你就完成了 S3 存储的完整配置！ChewyAttachment 会自动使用 django-storages 提供的 S3 后端，支持文件上传、下载、删除和 URL 生成等所有功能。