#
# 性能分散：S3 会根据前缀（Prefix）来划分索引。如果前缀是随机的，请求会均匀分布到不同的节点上，避免了所谓的 "Hot Partition"。
# 
# 按天分区：在随机前缀之后加入日期（如 20251002），是为了方便你后续使用 Amazon Athena 或 Glue 进行日志分析。
# 
# 成本考虑：虽然路径长短不影响存储费，但建议路径不要包含太多层级（深度过大），保持在 5-8 层左右最利于维护。
#
# 确保你的机器已经配置了 AWS 凭证（通过 aws configure 或 环境变量）。
# 
# 如果日志文件非常大（超过 100MB），建议改用 s3_client.upload_file，它会自动处理分段上传（Multipart Upload）。
#

import boto3
import hashlib
import os
from datetime import datetime
from botocore.exceptions import ClientError

def generate_s3_path(log_type, file_content, sequence):
    """
    生成符合 S3 最佳实践的路径：[hash_prefix]/[log_type]/[YYYYMMDD]/[filename]
    """
    # 1. 生成基于 sequence 的哈希前缀 (取前 3 位足够分散几千个分片)
    hash_prefix = hashlib.md5(str(sequence).encode()).hexdigest()[:3]
    
    # 2. 获取当前日期
    datestr = datetime.now().strftime('%Y%m%d')
    
    # 3. 构造路径
    # 路径示例: a3f/error_logs/20260202/log_1024.log
    return f"{hash_prefix}/{log_type}/{datestr}/log_{sequence}.log"

def upload_to_s3(bucket_name, log_type, content, sequence):
    s3_client = boto3.client('s3')
    
    target_path = generate_s3_path(log_type, content, sequence)
    
    try:
        # 直接上传字符串内容到 S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=target_path,
            Body=content,
            ContentType='text/plain'
        )
        print(f"Successfully uploaded to: s3://{bucket_name}/{target_path}")
    except ClientError as e:
        print(f"Upload failed: {e}")
        return False
    return True

# --- 使用示例 ---
if __name__ == "__main__":
    MY_BUCKET = "your-app-logs-bucket"
    LOG_DATA = "yyyy-mm-dd hh:mm:ss - ERROR - Database connection timeout."
    
    upload_to_s3(MY_BUCKET, "api_logs", LOG_DATA, sequence=45678)
