def check_ip_reachable(ip_addr, port, timeout=3):
    """
    综合检查：先试 TCP 端口，失败再试 Ping
    """
    # 先试 TCP 连接
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((ip_addr, port))
    sock.close()
    
    if result == 0:
        return True, f"TCP port {port} reachable"
    
    # TCP 失败，尝试 Ping（如果 ping3 已安装）
    try:
        from ping3 import ping
        delay = ping(ip_addr, timeout=timeout)
        if delay is not None:
            return True, f"Ping reachable，the deply: {delay*1000:.2f}ms"
    except:
        pass
    
    return False, f"{ip_addr} unreachable（TCP port {port} and Ping failed）"

ip_addr = input("Enter the ip address here:")
port = int(input("Enter the port number here:"))

# 测试
print(check_ip_reachable(ip_addr, port))   # DNS 端口通常是通的
