#!/usr/bin/env python3
"""
Django Example 端到端测试

在 Django example 服务中测试：
1. 多 S3 配置是否正常工作
2. 数据同步功能是否可用
"""

import os
import sys
import subprocess
import time
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

# 切换到 django_example 目录
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples", "django_example"))
sys.path.insert(0, os.getcwd())

# 初始化 Django
import django
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

# 确保测试用户存在
if not User.objects.filter(username='testuser').exists():
    User.objects.create_superuser('testuser', 'test@example.com', 'testpass123')

print("\n" + "=" * 70)
print("Django Example 端到端测试")
print("=" * 70)

# 使用 Django Test Client
client = Client()

# 登录
login_success = client.login(username='testuser', password='testpass123')
print(f"\n登录状态: {'✓ 成功' if login_success else '✗ 失败'}")

if not login_success:
    print("无法登录，测试终止")
    sys.exit(1)


def test_health_check():
    """测试健康检查接口"""
    print("\n" + "-" * 50)
    print("测试 1: 健康检查接口")
    print("-" * 50)
    
    response = client.get('/api/attachments/health/')
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"服务状态: {data.get('status')}")
        print(f"版本: {data.get('version')}")
        print(f"数据库: {data.get('checks', {}).get('database', {}).get('status')}")
        print(f"存储: {data.get('checks', {}).get('storage', {}).get('status')}")
        return True
    else:
        print(f"错误: {response.content}")
        return False


def test_upload_to_different_s3():
    """测试上传到不同的 S3 存储"""
    print("\n" + "-" * 50)
    print("测试 2: 上传文件到不同的 S3 存储")
    print("-" * 50)
    
    uploaded_files = []
    
    # 上传到 S3-Primary
    file1 = SimpleUploadedFile(
        "test_primary.txt",
        b"This file goes to S3 Primary (MinIO 1)",
        content_type="text/plain"
    )
    response1 = client.post('/api/attachments/files/', {
        'file': file1,
        'is_public': False,
        'storage_config_id': 's3-primary',
    })
    
    if response1.status_code == 201:
        data1 = response1.json()
        print(f"✓ 上传到 S3-Primary 成功")
        print(f"  ID: {data1['id']}")
        print(f"  存储配置: {data1.get('storage_config_id', 'N/A')}")
        uploaded_files.append(data1)
    else:
        print(f"✗ 上传到 S3-Primary 失败: {response1.status_code}")
        print(f"  错误: {response1.content.decode()}")
        return False, []
    
    # 上传到 S3-Secondary
    file2 = SimpleUploadedFile(
        "test_secondary.txt",
        b"This file goes to S3 Secondary (MinIO 2)",
        content_type="text/plain"
    )
    response2 = client.post('/api/attachments/files/', {
        'file': file2,
        'is_public': False,
        'storage_config_id': 's3-secondary',
    })
    
    if response2.status_code == 201:
        data2 = response2.json()
        print(f"✓ 上传到 S3-Secondary 成功")
        print(f"  ID: {data2['id']}")
        print(f"  存储配置: {data2.get('storage_config_id', 'N/A')}")
        uploaded_files.append(data2)
    else:
        print(f"✗ 上传到 S3-Secondary 失败: {response2.status_code}")
        print(f"  错误: {response2.content.decode()}")
        return False, uploaded_files
    
    return True, uploaded_files


def test_download_files(uploaded_files):
    """测试下载文件"""
    print("\n" + "-" * 50)
    print("测试 3: 下载文件验证")
    print("-" * 50)
    
    for file_info in uploaded_files:
        file_id = file_info['id']
        response = client.get(f'/api/attachments/files/{file_id}/content/')
        
        # 可能是重定向到 S3 预签名 URL
        if response.status_code in [200, 302]:
            print(f"✓ 文件 {file_id[:8]}... 可访问 (状态码: {response.status_code})")
        else:
            print(f"✗ 文件 {file_id[:8]}... 访问失败: {response.status_code}")
            return False
    
    return True


def test_storage_stats():
    """测试存储统计接口"""
    print("\n" + "-" * 50)
    print("测试 4: 存储统计接口")
    print("-" * 50)
    
    response = client.get('/api/attachments/stats/')
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ 统计接口正常")
        print(f"  范围: {data.get('scope')}")
        print(f"  总文件数: {data.get('total_files')}")
        print(f"  总大小: {data.get('total_size_human')}")
        
        by_storage = data.get('by_storage', [])
        if by_storage:
            print(f"  按存储分组:")
            for item in by_storage:
                print(f"    - {item.get('storage_config_id')}: {item.get('count')} 个文件, {item.get('size_human')}")
        return True
    else:
        print(f"✗ 统计接口失败: {response.status_code}")
        return False


def test_data_migration():
    """测试数据迁移功能"""
    print("\n" + "-" * 50)
    print("测试 5: 数据迁移功能")
    print("-" * 50)
    
    from chewy_attachment.django_app.models import Attachment
    from chewy_attachment.django_app.storage import get_storage_manager
    from chewy_attachment.core.storage import StorageMigrator
    
    # 获取 S3-Primary 的文件
    primary_files = Attachment.objects.filter(storage_config_id='s3-primary')
    
    if not primary_files.exists():
        print("没有 S3-Primary 的文件可迁移，跳过测试")
        return True
    
    print(f"找到 {primary_files.count()} 个 S3-Primary 文件待迁移")
    
    # 创建迁移器
    manager = get_storage_manager()
    migrator = StorageMigrator(manager)
    
    # 记录迁移前的状态
    files_to_migrate = list(primary_files)
    
    # 定义更新回调
    def update_callback(attachment_id, new_path, new_config_id):
        Attachment.objects.filter(id=attachment_id).update(
            storage_path=new_path,
            storage_config_id=new_config_id,
        )
        print(f"  📝 更新记录: {attachment_id[:8]}... -> {new_config_id}")
    
    # 执行迁移
    summary = migrator.sync_to_target(
        attachments=files_to_migrate,
        target_config_id="s3-secondary",
        update_callback=update_callback,
        delete_source=True,
    )
    
    print(f"\n迁移结果:")
    print(f"  成功: {summary.success_count}")
    print(f"  失败: {summary.failed_count}")
    print(f"  跳过: {summary.skipped_count}")
    
    if summary.failed_count > 0:
        print("\n失败详情:")
        for r in summary.results:
            if not r.success:
                print(f"  - {r.original_name}: {r.error}")
        return False
    
    # 验证迁移后的文件
    for file_info in files_to_migrate:
        updated = Attachment.objects.get(id=file_info.id)
        if updated.storage_config_id != 's3-secondary':
            print(f"✗ 文件 {file_info.id} 的 storage_config_id 未更新")
            return False
    
    print("✓ 所有文件迁移成功并更新记录")
    return True


def cleanup_test_files():
    """清理测试文件"""
    print("\n" + "-" * 50)
    print("清理测试文件")
    print("-" * 50)
    
    from chewy_attachment.django_app.models import Attachment
    from chewy_attachment.django_app.storage import get_storage_engine_for_attachment
    
    test_files = Attachment.objects.filter(
        original_name__startswith='test_'
    )
    
    for att in test_files:
        try:
            storage = get_storage_engine_for_attachment(att.storage_config_id)
            storage.delete_file(att.storage_path)
            att.delete()
            print(f"  ✓ 删除: {att.original_name}")
        except Exception as e:
            print(f"  ✗ 删除失败 {att.original_name}: {e}")
    
    print("清理完成")


def main():
    results = []
    
    # 测试 1: 健康检查
    results.append(("健康检查接口", test_health_check()))
    
    # 测试 2: 上传到不同 S3
    success, uploaded_files = test_upload_to_different_s3()
    results.append(("上传到不同 S3", success))
    
    if success:
        # 测试 3: 下载验证
        results.append(("下载文件验证", test_download_files(uploaded_files)))
        
        # 测试 4: 存储统计
        results.append(("存储统计接口", test_storage_stats()))
        
        # 测试 5: 数据迁移
        results.append(("数据迁移功能", test_data_migration()))
    
    # 清理
    cleanup_test_files()
    
    # 汇总
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("❌ 部分测试失败")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
