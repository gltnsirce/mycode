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
