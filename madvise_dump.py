#!/usr/bin/env python3
import os
import sys

pid = int(sys.argv[1])
addr = int(sys.argv[2], 16)
size = int(sys.argv[3]) * 1024  # KB to bytes

# 打开进程内存文件
with open(f"/proc/{pid}/mem", "rb+") as mem:
    # 尝试写入零（不代表安全释放）
    mem.seek(addr)
    # 危险操作！仅用于演示
    # mem.write(b'\x00' * size)
