import socket

def check_port(ip, port, timeout=3):
    """
    测试指定 IP 的端口是否可达
    返回: (是否可达, 错误信息)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            return True, f"The port:{port} is reachable."
        else:
            return False, f"The port:{port} is unreachable. (the exception is {result})"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

# 使用示例
ip = input("please type the ip address:")
port = int(input("please enter the port number:"))

reachable, msg = check_port(ip, port)
print(f"{ip}:{port} -> {msg}")
