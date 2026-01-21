# Django S3 存储示例

这个示例展示了如何在 Django 项目中使用 ChewyAttachment 配合 AWS S3 存储。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 AWS 配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### 3. 运行迁移

```bash
python manage.py migrate
```

### 4. 测试 S3 配置

```bash
# 测试 S3 连接
python manage.py test_s3_storage --cleanup
```

### 5. 创建超级用户（可选）

```bash
python manage.py createsuperuser
```

### 6. 启动服务器

```bash
python manage.py runserver
```

## API 测试

### 上传文件

```bash
curl -X POST http://localhost:8000/api/attachments/files/ \
  -H "Authorization: Bearer your-token" \
  -F "file=@test.jpg" \
  -F "is_public=true"
```

### 获取文件列表

```bash
curl http://localhost:8000/api/attachments/files/
```

### 下载文件

```bash
curl http://localhost:8000/api/attachments/files/{file_id}/content/
```

## 配置说明

这个示例使用了以下配置：

- **存储引擎**: `django` (使用 django-storages)
- **存储后端**: AWS S3
- **文件权限**: 私有文件，使用签名 URL 访问
- **URL 过期**: 1小时

查看 `settings.py` 了解详细配置。

## 故障排除

### 1. S3 权限错误

确保你的 AWS 用户有以下权限：

- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`
- `s3:ListBucket`

### 2. CORS 问题

如果从浏览器上传文件，需要在 S3 存储桶中配置 CORS：

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "POST", "PUT", "DELETE"],
        "AllowedOrigins": ["http://localhost:8000"],
        "ExposeHeaders": []
    }
]
```

### 3. 签名 URL 不工作

检查以下设置：

```python
AWS_QUERYSTRING_AUTH = True
AWS_DEFAULT_ACL = 'private'
```

## 生产环境建议

1. **使用 IAM 角色**：在 EC2 或 ECS 中使用 IAM 角色而不是访问密钥
2. **启用 CloudFront**：使用 CDN 加速文件访问
3. **设置生命周期策略**：自动删除过期文件
4. **启用版本控制**：防止意外删除
5. **监控成本**：设置 S3 成本警报