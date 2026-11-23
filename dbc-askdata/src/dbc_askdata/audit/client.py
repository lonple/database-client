from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


class AuditClient:
    """经 mTLS 上报业务审计事件到 dbc-audit /inner/events。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tmpdir = tempfile.TemporaryDirectory(prefix="askdata-mtls-")
        self._cert_pem, self._key_pem = self._materialize_pem(settings)

    def _materialize_pem(self, settings: Settings) -> tuple[Path, Path]:
        p12_path = settings.mtls_client_p12()
        pass_path = settings.mtls_client_pass()
        if not p12_path.is_file():
            raise RuntimeError(
                f"审计已启用但缺少客户端证书: {p12_path}。"
                f"请在用户中心为应用 {settings.audit_client_id} 签发 mTLS 证书到 secrets/mtls/clients/。"
            )
        password = b""
        if pass_path.is_file():
            password = pass_path.read_text(encoding="utf-8").strip().encode("utf-8")
        key, cert, _ = pkcs12.load_key_and_certificates(p12_path.read_bytes(), password)
        if key is None or cert is None:
            raise RuntimeError(f"无法从 p12 加载密钥/证书: {p12_path}")
        cert_pem = Path(self._tmpdir.name) / "client.crt"
        key_pem = Path(self._tmpdir.name) / "client.key"
        cert_pem.write_bytes(cert.public_bytes(Encoding.PEM))
        key_pem.write_bytes(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
        return cert_pem, key_pem

    async def emit_biz(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        operator_user_id: int,
        operator_username: str = "",
        result: str = "SUCCESS",
        fail_reason: str | None = None,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        """入队异步上报；主流程不阻塞 mTLS HTTP。"""
        from dbc_askdata.observability.obs_queue import enqueue

        await enqueue(
            {
                "type": "audit_biz",
                "action": action,
                "resourceType": resource_type,
                "resourceId": str(resource_id),
                "operatorUserId": operator_user_id,
                "operatorUsername": operator_username or "",
                "result": result,
                "failReason": fail_reason,
                "details": details or {},
                "traceId": trace_id,
                "clientIp": client_ip,
            }
        )

    async def emit_biz_sync(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        operator_user_id: int,
        operator_username: str = "",
        result: str = "SUCCESS",
        fail_reason: str | None = None,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        """Worker 实际上报。"""
        event = {
            "eventId": str(uuid.uuid4()),
            "category": "BIZ",
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "operatorUserId": operator_user_id,
            "operatorUsername": operator_username or None,
            "clientIp": client_ip,
            "traceId": trace_id,
            "module": "askdata",
            "action": action,
            "resourceType": resource_type,
            "resourceId": str(resource_id),
            "result": result,
            "failReason": fail_reason,
            "details": details or {},
        }
        try:
            await self._post([event])
        except Exception:
            log.warning("审计事件上报失败 action=%s resource=%s", action, resource_id, exc_info=True)

    async def _post(self, events: list[dict[str, Any]]) -> None:
        url = self._settings.audit_mtls_base_url.rstrip("/") + "/inner/events"
        ca = self._settings.mtls_ca_cert()
        verify: Any = str(ca) if ca.is_file() else False
        async with httpx.AsyncClient(
            timeout=10.0,
            verify=verify,
            cert=(str(self._cert_pem), str(self._key_pem)),
            trust_env=False,
        ) as client:
            resp = await client.post(url, json={"events": events})
            if resp.status_code >= 400:
                raise RuntimeError(f"audit ingest HTTP {resp.status_code}: {resp.text[:300]}")
