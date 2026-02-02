import uuid
import hashlib

def get_optimized_log_path(log_type, timestamp, sequence):
    """
    生成优化后的日志文件路径，避免热点
    """
    # 方法1：使用UUID的前几位
    random_prefix = str(uuid.uuid4())[:3]  # 如 'a3f'
    
    # 方法2：基于序列号的哈希
    hash_prefix = hashlib.md5(str(sequence).encode()).hexdigest()[:2]  # 如 '8e'
    
    # 方法3：基于时间的反转（分散按分钟的写入）
    minute = timestamp.split(':')[1]  # 获取分钟数
    time_prefix = f"{int(minute):02d}"  # 如 '15'
    
    # 组合使用
    return f"{random_prefix}/logs/{log_type}/{timestamp}/{sequence}.log"
