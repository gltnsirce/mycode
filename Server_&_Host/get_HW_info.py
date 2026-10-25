import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("RedfishCollector")

class RedfishCollector:
    def __init__(self, host: str, user: str, password: str, semaphore: asyncio.Semaphore):
        self.host = host
        self.user = user
        self.password = password
        self.base_url = f"https://{host}"
        self.semaphore = semaphore
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None

    async def __aenter__(self):
        # 忽略自签名证书警告（生产环境建议配置信任的 CA 根证书）
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=20))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def login(self) -> bool:
        login_url = f"{self.base_url}/redfish/v1/SessionService/Sessions"
        payload = {"UserName": self.user, "Password": self.password}
        
        for attempt in range(3):
            try:
                async with self.session.post(login_url, json=payload) as resp:
                    if resp.status == 201:
                        self.token = resp.headers.get("X-Auth-Token")
                        self.session.headers.update({"X-Auth-Token": self.token})
                        return True
            except Exception as e:
                logger.warning(f"[{self.host}] 登录尝试 {attempt+1} 失败: {e}")
                await asyncio.sleep(2 ** attempt)
        return False

    async def fetch_with_retry(self, uri: str) -> Optional[Dict[Any, Any]]:
        url = f"{self.base_url}{uri}"
        max_retries = 3
        
        for attempt in range(max_retries):
            async with self.semaphore:  # 控制对该 BMC 或整体的并发
                try:
                    async with self.session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status == 401:
                            # Token 失效，尝试重新登录
                            if await self.login():
                                continue
                        elif resp.status in [429, 502, 503, 504]:
                            # 限速或服务端错误，指数退避
                            wait_time = (2 ** attempt) + (0.1 * attempt)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"[{self.host}] 访问 {uri} 返回状态码: {resp.status}")
                            return None
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"[{self.host}] 请求 {uri} 异常 (尝试 {attempt+1}): {e}")
                    await asyncio.sleep(2 ** attempt)
        return None

    async def collect_system_info(self) -> Dict[str, Any]:
        if not await self.login():
            return {"host": self.host, "status": "AUTH_FAILED"}

        # 示例：采集基本系统信息
        system_data = await self.fetch_with_retry("/redfish/v1/Systems/1")
        if not system_data:
            return {"host": self.host, "status": "UNREACHABLE_OR_UNSUPPORTED"}

        return {
            "host": self.host,
            "uuid": system_data.get("UUID"),
            "model": system_data.get("Model"),
            "serial_number": system_data.get("SerialNumber"),
            "status": "SUCCESS",
            "data": system_data
        }

