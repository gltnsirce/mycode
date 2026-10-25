
import asyncio
import time
import logging
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 模拟单个 BMC 查询函数（实际中可替换为异步 HTTP 请求 httpx 或异步子进程调用 ipmitool）
async def fetch_bmc_data(server_ip: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    模拟查询单台服务器的 BMC 电量与健康状态
    """
    start_time = time.time()
    try:
        # 使用 asyncio.wait_for 控制单台设备的超时
        async def _query():
            # ---------------------------------------------------------
            # 真实场景替换区：
            # 1. Redfish API: async with httpx.AsyncClient() as client: resp = await client.get(...)
            # 2. IPMI 命令行: proc = await asyncio.create_subprocess_exec('ipmitool', ...)
            # ---------------------------------------------------------
            await asyncio.sleep(0.5)  # 模拟网络延迟
            
            # 模拟随机异常或超时
            if server_ip == "192.168.1.55":  # 模拟某台机器故障
                raise ConnectionError("BMC connection refused")
                
            return {
                "ip": server_ip,
                "status": "success",
                "power_watts": 245.5,  # 模拟电量/功率
                "health": "OK",        # 硬件健康状态
                "latency": round(time.time() - start_time, 3)
            }

        return await asyncio.wait_for(_query(), timeout=timeout)
        
    except asyncio.TimeoutError:
        logger.warning(f"Server {server_ip} BMC query timed out after {timeout}s")
        return {"ip": server_ip, "status": "timeout", "power_watts": None, "health": "UNKNOWN"}
    except Exception as e:
        logger.error(f"Server {server_ip} BMC query failed: {str(e)}")
        return {"ip": server_ip, "status": "error", "error_msg": str(e), "power_watts": None, "health": "UNKNOWN"}

async def worker(server_ip: str, semaphore: asyncio.Semaphore, results: List[Dict], timeout: float):
    """
    工作协程：受信号量保护的任务包装器
    """
    async with semaphore:
        result = await fetch_bmc_data(server_ip, timeout=timeout)
        results.append(result)

async def main():
    # 1. 模拟生成 10000 台服务器的 IP 列表
    total_servers = 10000
    server_ips = [f"10.100.{(i // 256) % 256}.{i % 256}" for i in range(total_servers)]
    
    # 2. 核心并发控制参数
    MAX_CONCURRENCY = 150      # 同时并发的最大 BMC 连接数（根据网卡和 BMC 性能调整）
    TIMEOUT_PER_SERVER = 6.0   # 单台设备查询超时时间（秒）
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results = []
    
    logger.info(f"Start querying {total_servers} servers with max concurrency {MAX_CONCURRENCY}...")
    start_total = time.time()
    
    # 3. 创建所有任务
    tasks = [worker(ip, semaphore, results, TIMEOUT_PER_SERVER) for ip in server_ips]
    
    # 4. 并发执行所有任务 (return_exceptions=True 确保个别任务崩溃不影响整体)
    await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_total
    logger.info(f"Finished! Total time: {duration:.2f} seconds.")
    
    # 5. 统计结果
    success_count = sum(1 for r in results if r.get("status") == "success")
    timeout_count = sum(1 for r in results if r.get("status") == "timeout")
    error_count = sum(1 for r in results if r.get("status") == "error")
    
    logger.info(f"Stats -> Success: {success_count}, Timeout: {timeout_count}, Error: {error_count}")

if __name__ == "__main__":
    # 运行异步主循环
    asyncio.run(main())
