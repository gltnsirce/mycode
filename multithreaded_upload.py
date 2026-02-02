# ThreadPoolExecutor: 这是 Python 并发的核心。max_workers 建议设为 CPU核心数 * 2 到 CPU核心数 * 5 之间。如果网络带宽很大，可以设得更高。
#
# as_completed: 这是一个迭代器，哪个线程先传完就先返回结果，不会因为某个大文件的延迟阻塞整个循环。
#
# Client 实例化位置: 在多线程中，通常建议在 single_upload 内部实例化 boto3.client，或者使用 threading.local() 确保线程安全。Boto3 的 Session 对象在多线程下共享时偶尔会有并发问题。
# 
# 如果文件很大：不要用 put_object，请改用 s3_client.upload_file。Boto3 会自动启动它内部管理的 TransferConfig，那才是真正的“多线程分段上传”利器。
#
# 流量控制：如果你是在生产服务器上跑，记得限制 MAX_WORKERS，否则可能会瞬间占满带宽，影响业务服务的正常运行。
#
# TBD ...
#

import boto3
import hashlib
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 配置区 ---
BUCKET_NAME = "your-app-logs-bucket"
MAX_WORKERS = 10  # 并发线程数，根据带宽调整
BATCH_SIZE = 100  # 每批处理的任务数

def generate_s3_path(log_type, sequence):
    """生成优化后的 S3 路径"""
    hash_prefix = hashlib.md5(str(sequence).encode()).hexdigest()[:3]
    datestr = datetime.now().strftime('%Y%m%d')
    return f"{hash_prefix}/{log_type}/{datestr}/log_{sequence}.log"

def single_upload(log_item):
    """
    单个文件上传逻辑
    log_item 格式: (log_type, content, sequence)
    """
    log_type, content, sequence = log_item
    s3_client = boto3.client('s3')
    target_path = generate_s3_path(log_type, sequence)
    
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=target_path,
            Body=content,
            ContentType='text/plain'
        )
        return True, target_path
    except Exception as e:
        return False, f"Sequence {sequence} failed: {str(e)}"

def batch_upload_to_s3(log_data_list):
    """
    使用线程池并行上传
    """
    results = {"success": 0, "failure": 0}
    
    # 使用 ThreadPoolExecutor 管理线程
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有上传任务
        future_to_log = {executor.submit(single_upload, item): item for item in log_data_list}
        
        for future in as_completed(future_to_log):
            success, message = future.result()
            if success:
                results["success"] += 1
            else:
                print(f"[ERROR] {message}")
                results["failure"] += 1
                
    return results

# --- 模拟运行 ---
if __name__ == "__main__":
    # 模拟 50 条待上传的日志数据
    mock_logs = [
        ("sys_log", f"Log content for seq {i}", i) 
        for i in range(50)
    ]
    
    print(f"开始并行上传，并发数: {MAX_WORKERS}...")
    start_time = datetime.now()
    
    report = batch_upload_to_s3(mock_logs)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n--- 上传完成 ---")
    print(f"成功: {report['success']}")
    print(f"失败: {report['failure']}")
    print(f"总耗时: {duration:.2f} 秒")
