#!/usr/bin/env python3
"""
ChewyAttachment S3 存储使用示例

这个脚本展示了如何在 Django 项目中配置和使用 S3 存储。
"""

# Django 配置示例
DJANGO_SETTINGS_EXAMPLE = """
# settings.py

import os

# 1. 添加到 INSTALLED_APPS
INSTALLED_APPS = [
    # ... 其他应用
    'storages',  # django-storages
    'chewy_attachment.django_app',
]

# 2. AWS S3 配置
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# S3 设置
AWS_DEFAULT_ACL = 'private'  # 文件默认私有
AWS_S3_FILE_OVERWRITE = False  # 不覆盖同名文件
AWS_QUERYSTRING_AUTH = True  # 使用签名 URL
AWS_QUERYSTRING_EXPIRE = 3600  # 签名 URL 1小时过期

# 使用 S3 作为默认文件存储
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 3. ChewyAttachment 配置
CHEWY_ATTACHMENT = {
    'STORAGE_ENGINE': 'django',  # 使用 Django 存储系统
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_EXTENSIONS': ['.jpg', '.png', '.pdf', '.txt'],
}
"""

# 环境变量配置示例
ENV_EXAMPLE = """
# .env 文件
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
"""

# API 使用示例
API_USAGE_EXAMPLE = """
# 上传文件到 S3
curl -X POST http://localhost:8000/api/attachments/files/ \\
  -H "Authorization: Bearer your-token" \\
  -F "file=@example.jpg" \\
  -F "is_public=false"

# 响应示例
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_name": "example.jpg",
  "mime_type": "image/jpeg",
  "size": 102400,
  "owner_id": "123",
  "is_public": false,
  "created_at": "2026-01-21 10:30:00",
  "preview_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/preview/",
  "download_url": "/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/content/",
  "file_url": "https://your-bucket.s3.us-east-1.amazonaws.com/attachments/2026/01/21/550e8400-e29b-41d4-a716-446655440000.jpg?AWSAccessKeyId=...&Signature=...&Expires=..."
}

# 访问文件 (会重定向到 S3 签名 URL)
curl -L http://localhost:8000/api/attachments/files/550e8400-e29b-41d4-a716-446655440000/content/
"""

def main():
    """打印配置示例"""
    print("=" * 60)
    print("ChewyAttachment S3 存储配置示例")
    print("=" * 60)
    
    print("\n1. Django 配置 (settings.py):")
    print(DJANGO_SETTINGS_EXAMPLE)
    
    print("\n2. 环境变量配置 (.env):")
    print(ENV_EXAMPLE)
    
    print("\n3. API 使用示例:")
    print(API_USAGE_EXAMPLE)
    
    print("\n4. 安装依赖:")
    print("pip install 'chewy-attachment[django-s3]'")
    
    print("\n5. 测试 S3 配置:")
    print("python manage.py test_s3_storage --cleanup")
    
    print("\n6. 支持的云存储服务:")
    print("- AWS S3")
    print("- MinIO")
    print("- 阿里云 OSS (S3 兼容接口)")
    print("- DigitalOcean Spaces")
    print("- 其他 S3 兼容服务")
    
    print("\n详细文档: docs/S3_STORAGE.md")
    print("=" * 60)


if __name__ == "__main__":
    main()