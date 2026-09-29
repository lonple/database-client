from __future__ import annotations

import asyncio
import logging
import os
import socket

import httpx

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)

# Nacos 3.x 客户端 OpenAPI（不再兼容 v1/v2 HTTP 命名接口）
_REGISTER_PATH = "/nacos/v3/client/ns/instance"
_LIST_PATH = "/nacos/v3/client/ns/instance/list"


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


class NacosRegistrar:
    """Nacos 3.x HTTP 客户端注册，供网关 lb://dbc-askdata 发现与负载均衡。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._addr = (settings.nacos_addr or os.getenv("DBC_NACOS_ADDR") or "").strip()
        self._ip = os.getenv("DBC_ASKDATA_NACOS_IP") or _local_ip()
        self._port = settings.port
        self._service = "dbc-askdata"
        self._group = os.getenv("DBC_ASKDATA_NACOS_GROUP", "DEFAULT_GROUP")
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._registered = False

    @property
    def enabled(self) -> bool:
        return bool(self._settings.nacos_register and self._addr)

    async def start(self) -> None:
        if not self.enabled:
            log.info("Nacos 注册未启用（DBC_ASKDATA_NACOS_REGISTER / DBC_NACOS_ADDR）")
            return
        await self._register(heart_beat=False)
        self._task = asyncio.create_task(self._heartbeat_loop(), name="nacos-heartbeat")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.enabled and self._registered:
            await self._deregister()

    def _base(self) -> str:
        host = self._addr
        if not host.startswith("http"):
            host = f"http://{host}"
        return host.rstrip("/")

    def _instance_params(self, *, heart_beat: bool) -> dict[str, str]:
        params: dict[str, str] = {
            "serviceName": self._service,
            "groupName": self._group,
            "ip": self._ip,
            "port": str(self._port),
            "clusterName": "DEFAULT",
            "heartBeat": "true" if heart_beat else "false",
        }
        if not heart_beat:
            params.update(
                {
                    "healthy": "true",
                    "enabled": "true",
                    "weight": "1.0",
                    "metadata": '{"preserved.register.source":"PYTHON","version":"0.1.0"}',
                }
            )
        return params

    async def _register(self, *, heart_beat: bool) -> None:
        url = f"{self._base()}{_REGISTER_PATH}"
        params = self._instance_params(heart_beat=heart_beat)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, params=params)
                body = resp.text
                if resp.status_code >= 400:
                    log.warning(
                        "Nacos %s 失败 status=%s body=%s",
                        "续约" if heart_beat else "注册",
                        resp.status_code,
                        body[:300],
                    )
                    # 续约发现实例被摘除：重新完整注册
                    if heart_beat and ("21003" in body or resp.status_code == 404):
                        self._registered = False
                        await self._register(heart_beat=False)
                    return
                data_ok = '"data":"ok"' in body.replace(" ", "") or '"data": "ok"' in body
                if not data_ok and "success" not in body.lower():
                    log.warning("Nacos 注册响应异常 body=%s", body[:300])
                self._registered = True
                if not heart_beat:
                    log.info(
                        "已注册 Nacos 3 service=%s group=%s ip=%s port=%s",
                        self._service,
                        self._group,
                        self._ip,
                        self._port,
                    )
        except Exception:
            log.warning("Nacos %s失败", "续约" if heart_beat else "注册", exc_info=True)

    async def _deregister(self) -> None:
        url = f"{self._base()}{_REGISTER_PATH}"
        params = {
            "serviceName": self._service,
            "groupName": self._group,
            "ip": self._ip,
            "port": str(self._port),
            "clusterName": "DEFAULT",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.delete(url, params=params)
            self._registered = False
            log.info("已注销 Nacos service=%s", self._service)
        except Exception:
            log.warning("Nacos 注销失败", exc_info=True)

    async def _heartbeat_loop(self) -> None:
        # Nacos 3：注册与续约同一接口，heartBeat=true；默认心跳间隔约 5s
        while not self._stop.is_set():
            if self._registered:
                await self._register(heart_beat=True)
            else:
                await self._register(heart_beat=False)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=5.0)
            except TimeoutError:
                continue
