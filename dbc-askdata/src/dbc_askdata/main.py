from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbc_askdata.api import (
    admin,
    document_routes,
    eval_routes,
    routes,
)
from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.audit.client import AuditClient
from dbc_askdata.config import get_settings
from dbc_askdata.db.migrate import ensure_schema
from dbc_askdata.db.session import engine
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.metrics import metrics_payload
from dbc_askdata.observability.trace import resolve_trace_id

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _ensure_stdio_utf8() -> None:
    """Windows 控制台默认 GBK，中文日志易乱码；尽量切到 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


class _QuietAccessFilter(logging.Filter):
    """高频轮询/探活不写 access 日志，避免刷屏。"""

    _SKIP = ("/work-logs", "/health", "/metrics")

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(s in msg for s in self._SKIP)


def _configure_logging(level_name: str | None = None) -> None:
    _ensure_stdio_utf8()
    name = (level_name or get_settings().log_level or "INFO").upper()
    level = getattr(logging, name, None)
    if not isinstance(level, int):
        level = logging.INFO
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)
    # httpx/httpcore 默认跟根 logger，INFO 会刷满出站请求行；只保留错误
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    access = logging.getLogger("uvicorn.access")
    access.addFilter(_QuietAccessFilter())


_configure_logging()
log = logging.getLogger("dbc_askdata")

# 进程级单例（启动时初始化）
llm_client: LlmClient | None = None
audit_client: AuditClient | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global llm_client, audit_client
    settings = get_settings()
    _configure_logging(settings.log_level)
    if settings.llm_residency == "cloud" and settings.sample_tool_enabled():
        raise RuntimeError("启动断言失败: residency=cloud 时不得启用 sample_columns")
    settings.assert_llm_ready()
    from dbc_askdata.security.auth import JwtService

    JwtService(settings)

    from dbc_askdata.agent_bundle import get_agent_bundle, reload_agent_bundle
    from dbc_askdata.llm.registry import resolve_model_name
    from dbc_askdata.redis.client import close_redis, init_redis

    if settings.audit_enabled:
        audit_client = AuditClient(settings)
        log.info("审计客户端已启用 -> %s", settings.audit_mtls_base_url)
    else:
        audit_client = None
        log.warning("DBC_ASKDATA_AUDIT_ENABLED=false，业务审计不上报（仅允许显式关闭）")

    migration_dir = settings.resolved_migrations_dir()
    if not migration_dir.is_dir():
        raise RuntimeError(f"缺少迁移目录: {migration_dir}")
    await ensure_schema(engine, settings.database_schema, migration_dir)

    await init_redis(settings)

    from dbc_askdata.observability.obs_queue import start_obs_worker, stop_obs_worker

    await start_obs_worker()

    from dbc_askdata.documents.worker import reclaim_stale_jobs

    await reclaim_stale_jobs()

    from dbc_askdata.app_config import runtime_override
    from dbc_askdata.app_config.service import load_askdata_config
    from dbc_askdata.concurrency.chat_gate import refresh_chat_semaphore
    from dbc_askdata.db.session import SessionLocal
    from dbc_askdata.httpx_pool import close_all_httpx_clients, httpx_max_connections

    try:
        async with SessionLocal() as session:
            runtime_cfg = await load_askdata_config(session, use_cache=False)
        refresh_chat_semaphore(runtime_cfg.concurrent_chat_limit)
        runtime_override.set_llm_provider(runtime_cfg.llm_provider)
        log.info(
            "应用配置已加载 provider=%s daily_token=%s concurrent_chat=%s httpx_max=%s",
            runtime_cfg.llm_provider,
            runtime_cfg.daily_token_limit,
            runtime_cfg.concurrent_chat_limit,
            httpx_max_connections(),
        )
    except Exception:
        log.error("加载问数应用配置失败，使用默认并发闸", exc_info=True)
        refresh_chat_semaphore(20)

    reload_agent_bundle()
    llm_client = LlmClient(settings)
    bundle = get_agent_bundle()

    # 预建下游连接，避免首轮 TOOL（ada-memory / sqlwork）冷 TCP+TLS
    try:
        from dbc_askdata.httpx_pool import warmup_shared_clients

        warm_targets: list[tuple[str, str, float]] = []
        mem = (settings.ada_memory_base_url or "").rstrip("/")
        if mem:
            warm_targets.append(
                ("ada-memory", f"{mem}/api/health", float(settings.ada_memory_timeout_seconds))
            )
        sw = (settings.sqlwork_base_url or "").rstrip("/")
        if sw:
            warm_targets.append(
                ("sqlwork", f"{sw}/actuator/health", float(settings.sqlwork_timeout_seconds))
            )
        graph = (settings.ada_graph_base_url or "").rstrip("/")
        if graph:
            warm_targets.append(
                ("ada-graph", f"{graph}/api/health", float(settings.ada_graph_timeout_seconds))
            )
        if warm_targets:
            await warmup_shared_clients(warm_targets)
    except Exception:
        log.warning("httpx warmup 阶段异常（忽略）", exc_info=True)

    if settings.eval_seed_on_startup:
        from dbc_askdata.eval.templates import seed_eval_templates

        try:
            async with SessionLocal() as session:
                await seed_eval_templates(session, settings)
        except Exception:
            log.error("测评模板/用例种子导入失败", exc_info=True)
            raise

    from dbc_askdata.discovery.nacos import NacosRegistrar

    registrar = NacosRegistrar(settings)
    await registrar.start()
    log.info(
        "dbc-askdata 启动完成 port=%s residency=%s provider=%s model=%s light=%s",
        settings.port,
        settings.llm_residency,
        getattr(llm_client, "provider_id", None) or settings.llm_provider,
        resolve_model_name(settings, tier="default"),
        resolve_model_name(settings, tier="light"),
    )
    yield
    await registrar.stop()
    await stop_obs_worker()
    await close_all_httpx_clients()
    await close_redis()
    await engine.dispose()


app = FastAPI(title="dbc-askdata", version="0.1.0", lifespan=lifespan)
app.include_router(routes.router)
app.include_router(eval_routes.router)
app.include_router(document_routes.router)
app.include_router(admin.router)
from dbc_askdata.api import app_config_routes

app.include_router(app_config_routes.router)


@app.middleware("http")
async def downstream_auth_middleware(request: Request, call_next):
    from dbc_askdata.clients.downstream_auth import (
        reset_downstream_authorization,
        set_downstream_authorization,
    )

    token = set_downstream_authorization(request.headers.get("Authorization"))
    try:
        return await call_next(request)
    finally:
        reset_downstream_authorization(token)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """入站解析/生成 TraceId，写入 request.state，并在响应头回写 X-Trace-Id。"""
    tid = resolve_trace_id(request.headers.get("X-Trace-Id"))
    request.state.trace_id = tid
    response = await call_next(request)
    response.headers["X-Trace-Id"] = tid
    return response


@app.get("/health")
async def health():
    return {"status": "UP", "service": "dbc-askdata"}


@app.get("/metrics")
async def metrics():
    settings = get_settings()
    if not settings.metrics_enabled:
        return JSONResponse({"message": "metrics disabled"}, status_code=404)
    body, content_type = metrics_payload()
    return Response(content=body, media_type=content_type)


@app.exception_handler(HTTPException)
async def http_ex(request: Request, ex: HTTPException):
    if isinstance(ex.detail, dict):
        msg = str(ex.detail.get("message") or ex.detail)
        body = ApiResponse.fail(msg).model_dump()
        body["data"] = ex.detail
        return JSONResponse(status_code=ex.status_code, content=body)
    detail = ex.detail if isinstance(ex.detail, str) else str(ex.detail)
    return JSONResponse(
        status_code=ex.status_code,
        content=ApiResponse.fail(detail).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, ex: Exception):
    log.error("未捕获异常 path=%s", request.url.path, exc_info=True)
    return JSONResponse(status_code=500, content=ApiResponse.fail("服务内部错误").model_dump())
