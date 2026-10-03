from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbc_askdata.api import admin, eval_routes, knowledge_routes, routes
from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.audit.client import AuditClient
from dbc_askdata.config import get_settings
from dbc_askdata.db.migrate import ensure_schema
from dbc_askdata.db.session import engine
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.metrics import metrics_payload
from dbc_askdata.observability.trace import resolve_trace_id

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _configure_logging(level_name: str | None = None) -> None:
    name = (level_name or get_settings().log_level or "INFO").upper()
    level = getattr(logging, name, None)
    if not isinstance(level, int):
        level = logging.INFO
    logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)
    logging.getLogger().setLevel(level)


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
    llm_client = LlmClient(settings)
    if settings.audit_enabled:
        audit_client = AuditClient(settings)
        log.info("审计客户端已启用 -> %s", settings.audit_mtls_base_url)
    else:
        audit_client = None
        log.warning("DBC_ASKDATA_AUDIT_ENABLED=false，业务审计不上报（仅允许显式关闭）")

    migration_dir = Path(__file__).resolve().parents[2] / "migrations"
    if not migration_dir.is_dir():
        raise RuntimeError(f"缺少迁移目录: {migration_dir}")
    await ensure_schema(engine, settings.database_schema, migration_dir)

    if settings.eval_seed_on_startup:
        from dbc_askdata.db.session import SessionLocal
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
        "dbc-askdata 启动完成 port=%s residency=%s model=%s",
        settings.port,
        settings.llm_residency,
        settings.llm_model,
    )
    yield
    await registrar.stop()
    await engine.dispose()


app = FastAPI(title="dbc-askdata", version="0.1.0", lifespan=lifespan)
app.include_router(routes.router)
app.include_router(eval_routes.router)
app.include_router(knowledge_routes.router)
app.include_router(admin.router)


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
    detail = ex.detail if isinstance(ex.detail, str) else str(ex.detail)
    return JSONResponse(
        status_code=ex.status_code,
        content=ApiResponse.fail(detail).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, ex: Exception):
    log.error("未捕获异常 path=%s", request.url.path, exc_info=True)
    return JSONResponse(status_code=500, content=ApiResponse.fail("服务内部错误").model_dump())
