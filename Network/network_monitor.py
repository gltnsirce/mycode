#!/usr/bin/env python3
"""   自动化网络质量监控脚本   """      
import subprocess   
import time   
import json   
from datetime import datetime      

defrun_command(cmd):
	"""执行命令并返回输出"""       
	try:
		result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)           
		return result.stdout.strip()
	except subprocess.TimeoutExpired:
		return"超时"
	except Exception as e:
		returnf"错误: {str(e)}"      

deftest_ping(target="8.8.8.8"):
	"""测试ping延迟"""
	cmd = f"ping -c 4 {target} | tail -1 | awk -F '/' '{{print $5}}'"
	latency = run_command(cmd)
	return {"target": target, "latency": latency}

deftest_speed():
	"""测试网速"""
	cmd = "speedtest-cli --json"
	result = run_command(cmd)
	try:
		data = json.loads(result)
		return {
			"download": data.get("download", 0) / 1000000,  # 转换为Mbps  
			"upload": data.get("upload", 0) / 1000000,
			"ping": data.get("ping", 0)
		}
	except:
		returnNone

defmain():
	"""主监控循环"""
	log_file = "/var/log/network_monitor.json"
	
	whileTrue:
		timestamp = datetime.now().isoformat()
		
		# 收集数据
		data = {
			"timestamp": timestamp,
			"ping": test_ping(),
			"speed": test_speed(),
			"interface": run_command("ip addr show | grep 'state UP'")           }
		# 记录到日志
		withopen(log_file, "a") as f:
			f.write(json.dumps(data) + "\n")
		
		# 检查阈值
		iffloat(data["ping"]["latency"]) > 100:
			print(f"警告: 延迟过高 - {data['ping']['latency']}ms")                 time.sleep(300)  # 5分钟间隔

if __name__ == "__main__":
	main()
