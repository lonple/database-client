from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError

from dbc_askdata.config import Settings, get_settings

log = logging.getLogger(__name__)

# 与 JJWT Keys.hmacShaKeyFor 一致：密钥长度决定 HS256/384/512
_JWT_ALGS = ("HS512", "HS384", "HS256")


@dataclass(frozen=True)
class LoginUser:
    user_id: int
    username: str
    role_codes: frozenset[str]
    permissions: frozenset[str]

    def has_permission(self, code: str) -> bool:
        if code in self.permissions:
            return True
        if code.endswith(".view"):
            operate = code[: -len(".view")] + ".operate"
            return operate in self.permissions
        return False


def _load_jwt_secret(settings: Settings) -> str:
    path = settings.jwt_secret_path()
    if not path.is_file():
        raise RuntimeError(f"JWT 密钥文件不存在: {path.resolve()}，请与 usercenter 共用 secrets/jwt-secret.txt")
    secret = path.read_text(encoding="utf-8").strip()
    if len(secret) < 32:
        raise RuntimeError("JWT 密钥长度不足，拒绝启动")
    return secret


class JwtService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._secret = _load_jwt_secret(settings)

    def parse(self, token: str) -> LoginUser:
        try:
            payload = jwt.decode(token, self._secret, algorithms=list(_JWT_ALGS))
        except InvalidTokenError as ex:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌") from ex
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌缺少主体")
        role_raw = payload.get("roleCodes") or payload.get("roleCode") or ""
        perm_raw = payload.get("permissions") or ""
        roles = frozenset(x.strip() for x in str(role_raw).split(",") if x.strip())
        perms = frozenset(x.strip() for x in str(perm_raw).split(",") if x.strip())
        return LoginUser(
            user_id=int(sub),
            username=str(payload.get("username") or ""),
            role_codes=roles,
            permissions=perms,
        )


_jwt_service: JwtService | None = None


def get_jwt_service(settings: Settings = Depends(get_settings)) -> JwtService:
    global _jwt_service
    if _jwt_service is None:
        _jwt_service = JwtService(settings)
    return _jwt_service


async def _fetch_permissions(settings: Settings, bearer: str) -> frozenset[str]:
    """与 manage UserContextFilter 对齐：JWT 不含权限码，按请求拉取 usercenter /auth/me。"""
    base = (settings.usercenter_base_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未配置 DBC_ASKDATA_USERCENTER_BASE_URL",
        )
    url = f"{base}/auth/me"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Authorization": bearer})
    except Exception as ex:
        log.warning("拉取 usercenter /auth/me 失败", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="拉取用户权限失败",
        ) from ex
    if resp.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或令牌失效")
    if resp.status_code >= 400:
        log.warning("usercenter /auth/me 异常 status=%s body=%s", resp.status_code, resp.text[:300])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="拉取用户权限失败",
        )
    try:
        body = resp.json()
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="拉取用户权限失败") from ex
    # ApiResponse: { code, data: { permissions: [...] } }
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return frozenset()
    raw = data.get("permissions") or []
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(x).strip() for x in raw if x and str(x).strip())


async def require_user(
    authorization: str | None = Header(default=None),
    jwt_service: JwtService = Depends(get_jwt_service),
    settings: Settings = Depends(get_settings),
) -> LoginUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user = jwt_service.parse(token)
    # JWT 通常无 permissions；与 manage 一样按请求向 usercenter 取权限并集
    perms = await _fetch_permissions(settings, authorization)
    if perms:
        return LoginUser(
            user_id=user.user_id,
            username=user.username,
            role_codes=user.role_codes,
            permissions=perms,
        )
    return user


def require_permission(code: str):
    async def _dep(user: LoginUser = Depends(require_user)) -> LoginUser:
        if not user.has_permission(code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {code}")
        return user

    return _dep


def extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return authorization
