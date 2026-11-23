"""把当前请求的用户 JWT 转给 dbc-knowledge / dbc-graph。"""

from __future__ import annotations

from contextvars import ContextVar

_authorization: ContextVar[str | None] = ContextVar("dbc_downstream_authorization", default=None)


def set_downstream_authorization(value: str | None):
    raw = (value or "").strip()
    if not raw:
        return _authorization.set(None)
    if not raw.lower().startswith("bearer "):
        raw = f"Bearer {raw}"
    return _authorization.set(raw)


def reset_downstream_authorization(token) -> None:
    _authorization.reset(token)


def authorization_headers() -> dict[str, str]:
    raw = _authorization.get()
    if not raw:
        return {}
    return {"Authorization": raw}


class AuthedHttp:
    """给共享 httpx 客户端补上当前请求的 Authorization。"""

    def __init__(self, raw) -> None:
        self._raw = raw

    def _merge(self, kwargs: dict) -> dict:
        headers = dict(authorization_headers())
        extra = kwargs.pop("headers", None)
        if extra:
            headers.update(extra)
        if headers:
            kwargs["headers"] = headers
        return kwargs

    def get(self, url, **kwargs):
        return self._raw.get(url, **self._merge(kwargs))

    def post(self, url, **kwargs):
        return self._raw.post(url, **self._merge(kwargs))

    def put(self, url, **kwargs):
        return self._raw.put(url, **self._merge(kwargs))

    def delete(self, url, **kwargs):
        return self._raw.delete(url, **self._merge(kwargs))
