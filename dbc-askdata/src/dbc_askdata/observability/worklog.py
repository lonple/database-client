from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

_lock = asyncio.Lock()
# session_id -> recent work log lines（进程内；供生成/执行过程轮询）
_logs: dict[int, list[dict[str, Any]]] = {}
_MAX = 200


async def clear_work_logs(session_id: int) -> None:
    async with _lock:
        _logs[session_id] = []


async def append_work_log(session_id: int | None, message: str, *, level: str = "INFO") -> None:
    if not session_id:
        return
    line = {
        "at": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
    }
    async with _lock:
        buf = _logs.setdefault(int(session_id), [])
        buf.append(line)
        if len(buf) > _MAX:
            del buf[: len(buf) - _MAX]


async def list_work_logs(session_id: int, *, after: int = 0) -> dict[str, Any]:
    async with _lock:
        buf = list(_logs.get(int(session_id), []))
    items = buf[after:] if after > 0 else buf
    return {"total": len(buf), "items": items, "next": len(buf)}
