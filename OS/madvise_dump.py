#!/usr/bin/env python3
import sys
import os

def safe_memory_write(pid, addr, size, data):
    """带安全检查的内存写入"""
    
    # 1. 检查进程是否存在
    if not os.path.exists(f"/proc/{pid}"):
        print(f"错误：进程 {pid} 不存在")
        return False
    
    # 2. 检查内存映射信息
    maps_file = f"/proc/{pid}/maps"
    with open(maps_file, 'r') as f:
        maps = f.read()
    
    # 3. 验证地址范围是否在可写区域内
    is_writable = False
    for line in maps.split('\n'):
        if '-' in line:
            range_str, perms = line.split()[:2]
            start, end = [int(x, 16) for x in range_str.split('-')]
            if start <= addr <= end and 'w' in perms:
                is_writable = True
                # 检查是否超出范围
                if addr + size > end:
                    print(f"警告：写入超出映射区域")
                break
    
    if not is_writable:
        print(f"错误：地址 {hex(addr)} 不在可写内存区域")
        return False
    
    # 4. 写入前备份（如果需要）
    # backup = read_memory(pid, addr, size)
    
    # 5. 执行写入
    with open(f"/proc/{pid}/mem", "rb+") as mem:
        mem.seek(addr)
        mem.write(data)
    
    print(f"成功写入 {size} 字节到进程 {pid}")
    return True

# 使用示例
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: {} <pid> <addr> <size_kb>".format(sys.argv[0]))
        sys.exit(1)
    
    pid = int(sys.argv[1])
    addr = int(sys.argv[2], 16)
    size = int(sys.argv[3]) * 1024
    
    # 写入零（但仍然危险）
    safe_memory_write(pid, addr, size, b'\x00' * size)
