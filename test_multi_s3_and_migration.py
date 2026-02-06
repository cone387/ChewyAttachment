#!/usr/bin/env python3
"""
测试多 S3 配置和数据同步功能

使用两个独立的 MinIO 实例：
- MinIO 1: localhost:9000 (minioadmin / minioadmin123)
- MinIO 2: localhost:9002 (minioadmin2 / minioadmin456)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boto3
from botocore.exceptions import ClientError
from pathlib import Path

# MinIO 配置
MINIO_1 = {
    "endpoint": "http://localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin123",
    "bucket": "bucket-s3-1",
}

MINIO_2 = {
    "endpoint": "http://localhost:9002",
    "access_key": "minioadmin2",
    "secret_key": "minioadmin456",
    "bucket": "bucket-s3-2",
}


def create_s3_client(config):
    """创建 S3 客户端"""
    return boto3.client(
        "s3",
        endpoint_url=config["endpoint"],
        aws_access_key_id=config["access_key"],
        aws_secret_access_key=config["secret_key"],
        region_name="us-east-1",
    )


def ensure_bucket_exists(config):
    """确保 bucket 存在"""
    client = create_s3_client(config)
    try:
        client.head_bucket(Bucket=config["bucket"])
        print(f"  ✓ Bucket '{config['bucket']}' 已存在于 {config['endpoint']}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=config["bucket"])
            print(f"  ✓ Bucket '{config['bucket']}' 创建成功于 {config['endpoint']}")
        else:
            raise


def test_multi_s3_config():
    """测试 1: 多 S3 配置是否正常工作"""
    print("\n" + "=" * 70)
    print("测试 1: 多 S3 配置")
    print("=" * 70)
    
    from chewy_attachment.core.storage import (
        StorageManager, StorageConfigProvider, S3StorageEngine
    )
    from chewy_attachment.core.schemas import S3ConfigSchema
    from chewy_attachment.core.exceptions import StorageException
    
    # 创建自定义 Provider
    class DualMinioProvider(StorageConfigProvider):
        def __init__(self):
            self._configs = {
                "s3-primary": S3ConfigSchema(
                    config_id="s3-primary",
                    bucket_name=MINIO_1["bucket"],
                    access_key=MINIO_1["access_key"],
                    secret_key=MINIO_1["secret_key"],
                    endpoint_url=MINIO_1["endpoint"],
                    prefix="primary-storage",
                ),
                "s3-secondary": S3ConfigSchema(
                    config_id="s3-secondary",
                    bucket_name=MINIO_2["bucket"],
                    access_key=MINIO_2["access_key"],
                    secret_key=MINIO_2["secret_key"],
                    endpoint_url=MINIO_2["endpoint"],
                    prefix="secondary-storage",
                ),
            }
        
        def get_config(self, config_id: str) -> S3ConfigSchema:
            if config_id not in self._configs:
                raise StorageException(f"Config '{config_id}' not found")
            return self._configs[config_id]
        
        def get_default_config(self):
            return self._configs["s3-primary"]
        
        def list_configs(self):
            return list(self._configs.keys())
    
    # 初始化 StorageManager
    StorageManager.reset_instance()
    provider = DualMinioProvider()
    manager = StorageManager(provider=provider, local_storage_root=Path("/tmp/test"))
    StorageManager.set_instance(manager)
    
    print("\n--- 测试上传到不同的 S3 存储 ---")
    
    # 上传到 S3-Primary (MinIO 1)
    engine1 = manager.get_engine("s3-primary")
    content1 = b"This file is stored in S3 Primary (MinIO 1)"
    result1 = engine1.save_file(content1, "primary_file.txt")
    print(f"  ✓ 上传到 S3-Primary: {result1.storage_path}")
    
    # 上传到 S3-Secondary (MinIO 2)
    engine2 = manager.get_engine("s3-secondary")
    content2 = b"This file is stored in S3 Secondary (MinIO 2)"
    result2 = engine2.save_file(content2, "secondary_file.txt")
    print(f"  ✓ 上传到 S3-Secondary: {result2.storage_path}")
    
    print("\n--- 验证文件存储在正确的位置 ---")
    
    # 验证文件在各自的存储中
    retrieved1 = engine1.get_file(result1.storage_path)
    assert retrieved1 == content1, "S3-Primary 文件内容不匹配"
    print(f"  ✓ S3-Primary 文件验证通过")
    
    retrieved2 = engine2.get_file(result2.storage_path)
    assert retrieved2 == content2, "S3-Secondary 文件内容不匹配"
    print(f"  ✓ S3-Secondary 文件验证通过")
    
    print("\n--- 验证文件隔离（跨存储不可访问）---")
    
    # 验证 S3-Primary 的文件在 S3-Secondary 中不存在
    assert not engine2.file_exists(result1.storage_path), "文件不应该在 S3-Secondary 中存在"
    print(f"  ✓ S3-Primary 文件在 S3-Secondary 中不存在（正确隔离）")
    
    # 验证 S3-Secondary 的文件在 S3-Primary 中不存在
    assert not engine1.file_exists(result2.storage_path), "文件不应该在 S3-Primary 中存在"
    print(f"  ✓ S3-Secondary 文件在 S3-Primary 中不存在（正确隔离）")
    
    print("\n--- 清理测试文件 ---")
    engine1.delete_file(result1.storage_path)
    engine2.delete_file(result2.storage_path)
    print(f"  ✓ 测试文件已清理")
    
    return True


def test_data_migration():
    """测试 2: 数据同步/迁移功能"""
    print("\n" + "=" * 70)
    print("测试 2: 数据同步/迁移功能")
    print("=" * 70)
    
    from chewy_attachment.core.storage import (
        StorageManager, StorageConfigProvider, StorageMigrator
    )
    from chewy_attachment.core.schemas import S3ConfigSchema
    from chewy_attachment.core.exceptions import StorageException
    
    # 创建 Provider
    class MigrationTestProvider(StorageConfigProvider):
        def __init__(self):
            self._configs = {
                "source-s3": S3ConfigSchema(
                    config_id="source-s3",
                    bucket_name=MINIO_1["bucket"],
                    access_key=MINIO_1["access_key"],
                    secret_key=MINIO_1["secret_key"],
                    endpoint_url=MINIO_1["endpoint"],
                    prefix="migration-source",
                ),
                "target-s3": S3ConfigSchema(
                    config_id="target-s3",
                    bucket_name=MINIO_2["bucket"],
                    access_key=MINIO_2["access_key"],
                    secret_key=MINIO_2["secret_key"],
                    endpoint_url=MINIO_2["endpoint"],
                    prefix="migration-target",
                ),
            }
        
        def get_config(self, config_id: str) -> S3ConfigSchema:
            if config_id not in self._configs:
                raise StorageException(f"Config '{config_id}' not found")
            return self._configs[config_id]
        
        def get_default_config(self):
            return self._configs["source-s3"]
        
        def list_configs(self):
            return list(self._configs.keys())
    
    # 初始化
    StorageManager.reset_instance()
    provider = MigrationTestProvider()
    manager = StorageManager(provider=provider, local_storage_root=Path("/tmp/test"))
    StorageManager.set_instance(manager)
    
    migrator = StorageMigrator(manager)
    source_engine = manager.get_engine("source-s3")
    target_engine = manager.get_engine("target-s3")
    
    print("\n--- 在源存储 (MinIO 1) 创建测试文件 ---")
    
    test_files = []
    for i in range(5):
        content = f"Migration test file {i} - 这是测试文件 {i}".encode("utf-8")
        result = source_engine.save_file(content, f"migrate_file_{i}.txt")
        test_files.append({
            "id": f"att-{i:03d}",
            "original_name": f"migrate_file_{i}.txt",
            "storage_config_id": "source-s3",
            "storage_path": result.storage_path,
            "content": content,
        })
        print(f"  ✓ 创建文件 {i+1}/5: {result.storage_path}")
    
    print("\n--- 执行数据迁移（从 MinIO 1 到 MinIO 2）---")
    
    def on_progress(current, total, result):
        status = "✓" if result.success else "✗"
        print(f"  {status} [{current}/{total}] {result.original_name}")
        if result.error and not result.success:
            print(f"      错误: {result.error}")
    
    summary = migrator.migrate_batch(
        attachments=test_files,
        target_config_id="target-s3",
        delete_source=True,  # 迁移后删除源文件
        on_progress=on_progress,
    )
    
    print(f"\n--- 迁移结果 ---")
    print(f"  总数: {summary.total}")
    print(f"  成功: {summary.success_count}")
    print(f"  失败: {summary.failed_count}")
    print(f"  跳过: {summary.skipped_count}")
    
    if summary.failed_count > 0:
        print("\n  失败详情:")
        for r in summary.results:
            if not r.success:
                print(f"    - {r.original_name}: {r.error}")
        return False
    
    print("\n--- 验证迁移结果 ---")
    
    # 验证目标存储中的文件
    for i, file_info in enumerate(test_files):
        result = summary.results[i]
        
        # 检查目标文件存在
        if not target_engine.file_exists(result.new_storage_path):
            print(f"  ✗ 目标文件不存在: {result.new_storage_path}")
            return False
        
        # 检查内容正确
        content = target_engine.get_file(result.new_storage_path)
        if content != file_info["content"]:
            print(f"  ✗ 文件内容不匹配: {result.new_storage_path}")
            return False
        
        # 检查源文件已删除
        if source_engine.file_exists(file_info["storage_path"]):
            print(f"  ✗ 源文件应该已删除: {file_info['storage_path']}")
            return False
    
    print(f"  ✓ 所有 {len(test_files)} 个文件迁移验证通过")
    print(f"  ✓ 源文件已全部删除")
    print(f"  ✓ 目标文件内容正确")
    
    print("\n--- 清理目标存储中的测试文件 ---")
    for result in summary.results:
        if result.new_storage_path:
            target_engine.delete_file(result.new_storage_path)
    print(f"  ✓ 测试文件已清理")
    
    return True


def test_sync_with_record_update():
    """测试 3: 同步并更新记录"""
    print("\n" + "=" * 70)
    print("测试 3: 同步并更新记录（模拟数据库更新）")
    print("=" * 70)
    
    from chewy_attachment.core.storage import (
        StorageManager, StorageConfigProvider, StorageMigrator
    )
    from chewy_attachment.core.schemas import S3ConfigSchema
    from chewy_attachment.core.exceptions import StorageException
    
    # 创建 Provider
    class SyncTestProvider(StorageConfigProvider):
        def __init__(self):
            self._configs = {
                "old-storage": S3ConfigSchema(
                    config_id="old-storage",
                    bucket_name=MINIO_1["bucket"],
                    access_key=MINIO_1["access_key"],
                    secret_key=MINIO_1["secret_key"],
                    endpoint_url=MINIO_1["endpoint"],
                    prefix="sync-old",
                ),
                "new-storage": S3ConfigSchema(
                    config_id="new-storage",
                    bucket_name=MINIO_2["bucket"],
                    access_key=MINIO_2["access_key"],
                    secret_key=MINIO_2["secret_key"],
                    endpoint_url=MINIO_2["endpoint"],
                    prefix="sync-new",
                ),
            }
        
        def get_config(self, config_id: str) -> S3ConfigSchema:
            if config_id not in self._configs:
                raise StorageException(f"Config '{config_id}' not found")
            return self._configs[config_id]
        
        def get_default_config(self):
            return self._configs["old-storage"]
        
        def list_configs(self):
            return list(self._configs.keys())
    
    # 初始化
    StorageManager.reset_instance()
    provider = SyncTestProvider()
    manager = StorageManager(provider=provider, local_storage_root=Path("/tmp/test"))
    StorageManager.set_instance(manager)
    
    migrator = StorageMigrator(manager)
    old_engine = manager.get_engine("old-storage")
    new_engine = manager.get_engine("new-storage")
    
    # 模拟数据库记录
    class MockAttachment:
        def __init__(self, id, original_name, storage_path, storage_config_id):
            self.id = id
            self.original_name = original_name
            self.storage_path = storage_path
            self.storage_config_id = storage_config_id
    
    print("\n--- 在旧存储创建用户文件 ---")
    
    attachments = []
    for i in range(3):
        content = f"User file {i} content".encode()
        result = old_engine.save_file(content, f"user_file_{i}.txt")
        attachments.append(MockAttachment(
            id=f"user-att-{i:03d}",
            original_name=f"user_file_{i}.txt",
            storage_path=result.storage_path,
            storage_config_id="old-storage",
        ))
        print(f"  ✓ 创建文件 {i+1}/3")
    
    # 模拟数据库更新
    db_records = {}
    
    def update_callback(attachment_id, new_path, new_config_id):
        """模拟数据库更新回调"""
        db_records[attachment_id] = {
            "storage_path": new_path,
            "storage_config_id": new_config_id,
        }
        print(f"  📝 更新记录: {attachment_id}")
        print(f"      新路径: {new_path}")
        print(f"      新配置: {new_config_id}")
    
    print("\n--- 执行同步（用户切换存储配置）---")
    
    summary = migrator.sync_to_target(
        attachments=attachments,
        target_config_id="new-storage",
        update_callback=update_callback,
        delete_source=True,
    )
    
    print(f"\n--- 同步结果 ---")
    print(f"  成功: {summary.success_count}")
    print(f"  记录更新: {len(db_records)}")
    
    # 验证
    if summary.success_count != 3:
        print(f"  ✗ 预期成功 3 个")
        return False
    
    if len(db_records) != 3:
        print(f"  ✗ 预期更新 3 条记录")
        return False
    
    # 验证记录更新正确
    for att in attachments:
        if att.id not in db_records:
            print(f"  ✗ 记录 {att.id} 未更新")
            return False
        
        record = db_records[att.id]
        if record["storage_config_id"] != "new-storage":
            print(f"  ✗ 记录 {att.id} 的 storage_config_id 不正确")
            return False
        
        # 验证新路径的文件存在
        if not new_engine.file_exists(record["storage_path"]):
            print(f"  ✗ 新路径文件不存在: {record['storage_path']}")
            return False
    
    print(f"  ✓ 所有记录已正确更新")
    print(f"  ✓ 新存储中的文件验证通过")
    
    print("\n--- 清理测试文件 ---")
    for record in db_records.values():
        new_engine.delete_file(record["storage_path"])
    print(f"  ✓ 测试文件已清理")
    
    return True


def main():
    print("\n" + "=" * 70)
    print("ChewyAttachment 多 S3 配置与数据同步测试")
    print("=" * 70)
    print("\nMinIO 实例配置:")
    print(f"  MinIO 1: {MINIO_1['endpoint']} (Bucket: {MINIO_1['bucket']})")
    print(f"  MinIO 2: {MINIO_2['endpoint']} (Bucket: {MINIO_2['bucket']})")
    
    try:
        print("\n--- 初始化 Buckets ---")
        ensure_bucket_exists(MINIO_1)
        ensure_bucket_exists(MINIO_2)
        
        results = []
        results.append(("多 S3 配置", test_multi_s3_config()))
        results.append(("数据迁移", test_data_migration()))
        results.append(("同步并更新记录", test_sync_with_record_update()))
        
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
            print("🎉 所有测试通过！多 S3 配置和数据同步功能工作正常。")
        else:
            print("❌ 部分测试失败。")
        print("=" * 70)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
