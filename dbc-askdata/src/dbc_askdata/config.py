from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DBC_ASKDATA_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "dbc-askdata"
    host: str = "0.0.0.0"
    port: int = 8009
    log_level: str = Field(
        default="INFO",
        description="根日志级别：DEBUG|INFO|WARNING|ERROR",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LOG_LEVEL",
            "LOG_LEVEL",
            "log_level",
        ),
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres",
        description="平台库 DSN（asyncpg）",
    )
    database_schema: str = "askdata"
    # 测评默认并发 20；单请求会占 1 条长连接 + 若干短连接（找表/观测），池过小会 QueuePool 超时
    db_pool_size: int = Field(
        default=20,
        ge=5,
        le=100,
        description="SQLAlchemy 连接池常驻连接数",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_DB_POOL_SIZE",
            "db_pool_size",
        ),
    )
    db_max_overflow: int = Field(
        default=40,
        ge=0,
        le=200,
        description="连接池最大溢出（总上限≈pool_size+max_overflow）",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_DB_MAX_OVERFLOW",
            "db_max_overflow",
        ),
    )
    db_pool_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        description="从池取连接的超时秒数",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_DB_POOL_TIMEOUT_SECONDS",
            "db_pool_timeout_seconds",
        ),
    )

    sqlwork_base_url: str = Field(default="http://127.0.0.1:8007")
    sqlwork_timeout_seconds: float = 60.0

    # ---- 知识库（旁路 ada-memory → Milvus ada_document / ada_slice）----
    ada_memory_base_url: str = Field(
        default="http://127.0.0.1:8010",
        description="dbc-knowledge 基址；创建/切片/发布后同步至 Milvus",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_KNOWLEDGE_BASE_URL",
            "DBC_ASKDATA_ADA_MEMORY_BASE_URL",
            "ADA_MEMORY_BASE_URL",
            "ada_memory_base_url",
        ),
    )
    ada_memory_timeout_seconds: float = Field(default=180.0)
    ada_memory_product_name: str = Field(
        default="dbc产品",
        description="问数调用 ada-memory 检索时的默认产品名",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_ADA_MEMORY_PRODUCT_NAME",
            "ADA_MEMORY_PRODUCT_NAME",
            "ada_memory_product_name",
        ),
    )
    # ---- 知识图谱（ada-graph：库表关系最短 JOIN 路径）----
    ada_graph_base_url: str = Field(
        default="http://127.0.0.1:8011",
        description="dbc-graph 基址",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_GRAPH_BASE_URL",
            "DBC_ASKDATA_ADA_GRAPH_BASE_URL",
            "ADA_GRAPH_BASE_URL",
            "ada_graph_base_url",
        ),
    )
    ada_graph_timeout_seconds: float = Field(default=30.0)
    graph_code: str = Field(
        default="default",
        description="问数固定使用的知识图谱编码",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_GRAPH_CODE",
            "graph_code",
        ),
    )
    # 鉴权拉权限：与 manage 一致走 usercenter /auth/me（JWT 不含 permissions）
    usercenter_base_url: str = Field(
        default="http://127.0.0.1:8004",
        description="dbc-usercenter 基址；生产可用网关或服务发现地址",
    )

    secrets_dir: str = Field(
        default="secrets",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_SECRETS_DIR",
            "DBC_SECRETS_DIR",
            "SECRETS_DIR",
            "secrets_dir",
        ),
    )
    jwt_expire_hours: int = 8

    # ---- LLM（Provider Profile：当前仅 qwen；默认云端）----
    llm_residency: str = Field(default="cloud", description="local | cloud")
    llm_provider: str = Field(
        default="qwen",
        description="厂商包 id：qwen；决定模型档位、Adapter 与整套提示词",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_PROVIDER",
            "ADA_LLM_PROVIDER",
            "llm_provider",
        ),
    )
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode",
        description="OpenAI 兼容根（可无 /v1）。空/千问默认且 provider≠qwen 时可用 profile.default_base_url",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_BASE_URL",
            "ADA_LLM_BASE_URL",
            "llm_base_url",
        ),
    )
    llm_model: str = Field(
        default="",
        description="覆盖 profile.models.default；空则用当前 provider 档位",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_MODEL",
            "ADA_LLM_CHAT_MODEL",
            "llm_model",
        ),
    )
    llm_api_key: str = Field(
        default="",
        description="优先环境变量；也可 secrets/askdata-llm-api-key.txt；兼容 ADA_LLM_API_KEY",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_API_KEY",
            "ADA_LLM_API_KEY",
            "llm_api_key",
        ),
    )
    llm_timeout_seconds: float = 120.0
    llm_max_tool_rounds: int = 8
    store_prompt: bool = False
    llm_model_light: str = Field(
        default="",
        description="覆盖 profile.models.light；空则用当前 provider 轻量档位",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_MODEL_LIGHT",
            "ADA_LLM_LIGHT_MODEL",
            "llm_model_light",
        ),
    )
    llm_profile_path: str = Field(
        default="",
        description="外部 Provider Profile 目录或 YAML；空则用包内 llm/providers/<llm_provider>",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_PROFILE_PATH",
            "llm_profile_path",
        ),
    )
    agent_bundle_path: str = Field(
        default="",
        description="已弃用：显式路径时作为 models/prompts overlay；请改用 llm_provider / llm_profile_path",
    )

    # ---- Redis（分布式锁 + 工具缓存；与平台 DBC_REDIS_* 对齐）----
    redis_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("DBC_ASKDATA_REDIS_ENABLED", "redis_enabled"),
    )
    redis_required: bool = Field(
        default=False,
        description="true 时 Redis 连不上拒绝启动",
    )
    redis_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_REDIS_HOST",
            "DBC_REDIS_HOST",
            "redis_host",
        ),
    )
    redis_port: int = Field(
        default=6379,
        validation_alias=AliasChoices(
            "DBC_ASKDATA_REDIS_PORT",
            "DBC_REDIS_PORT",
            "redis_port",
        ),
    )
    redis_password: str = Field(
        default="",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_REDIS_PASSWORD",
            "DBC_REDIS_PASSWORD",
            "redis_password",
        ),
    )
    redis_db: int = 0
    redis_key_prefix: str = "ask"
    tool_cache_ttl_seconds: int = 3600

    # ---- 用户日 LLM token 限额（上海自然日；0=关闭拦截）----
    daily_token_limit: int = Field(
        default=500_000,
        description="登录用户每日 LLM token（in+out）上限；0 关闭",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_DAILY_TOKEN_LIMIT",
            "daily_token_limit",
        ),
    )
    daily_token_track_when_unlimited: bool = False

    sample_enabled: str = "auto"  # auto：仅 local 开启；cloud 强制关闭
    sample_max_columns: int = 5
    sample_max_rows: int = 30

    # 列画像 / 枚举探测（模型按需触发 get_column_profile）
    profile_cache_ttl_seconds: int = 3600
    profile_enum_max_distinct: int = 64
    profile_enum_top_n: int = 30
    dict_cosine_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="字典 value 与条件值不相等时，余弦相似度达到该阈值才采用对应 key",
    )
    llm_embed_model: str = Field(
        default="text-embedding-v3",
        description="OpenAI 兼容 embeddings 模型，用于字典 value 余弦相似度",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_EMBED_MODEL",
            "ADA_LLM_EMBED_MODEL",
            "llm_embed_model",
        ),
    )

    # 遗留：盲修轮次（生成图已改为校验失败回 build/govern，默认不再走盲修）
    verify_max_repair_rounds: int = 3
    # 机械校验失败后，带 SQL+错误回生成阶段的最大次数
    verify_max_regen_rounds: int = 2
    sql_review_max_regen: int = 1
    workflow_run_row_limit: int = 1000
    allow_user_execute: bool = True
    temp_table_prefix: str = "askdata_tmp_"
    result_table_prefix: str = "askdata_rst_"
    rerun_cleanup: str = "drop_then_recreate"

    migrations_dir: str = Field(
        default="",
        description="SQL 迁移目录；空则按源码相对路径（editable）或 Docker 须显式 DBC_ASKDATA_MIGRATIONS_DIR",
    )

    # ---- 测评 ----
    eval_cases_dir: str = Field(
        default="scripts/demo-company/eval/cases",
        description="模板用例 JSONL 目录（相对仓库根或绝对路径）；空则跳过启动导入",
    )
    eval_expect_sql_timeout_ms: int = 60_000
    # 测评任务内用例并发默认值；运行时优先 ask_app_config.evalTaskConcurrency
    eval_task_concurrency: int = 20
    eval_seed_on_startup: bool = True

    # ---- 文档管理（原文目录；多副本须换对象存储，见架构概要已知不足）----
    documents_dir: str = Field(
        default="",
        description="原件与抽出图片根目录；空则 <secrets_dir 父目录>/data/askdata-documents",
    )
    document_max_bytes: int = 20 * 1024 * 1024
    document_convert_timeout_seconds: float = 180.0
    document_markdown_max_chars: int = 500_000
    document_xlsx_max_sheets: int = 20

    deep_agent_max_steps: int = 6

    # ---- 会话上下文压缩（轮内折叠 + 近窗问句/有用表）----
    context_tool_result_max_chars: int = Field(
        default=4000,
        description="单条 tool 结果写入 working 消息前的最大字符数",
    )
    context_working_budget_chars: int = Field(
        default=48_000,
        description="tool_agent 轮内 working messages 字符预算；超限折叠早期 tool 轮",
    )
    context_keep_recent_tool_rounds: int = Field(
        default=1,
        description="折叠时保留最近几轮含 tool_calls 的探测",
    )
    context_recent_turns: int = Field(
        default=10,
        description="跨轮注入的近窗条数上限（与 KEEP_WINDOW 对齐）",
    )
    context_recent_chars: int = Field(
        default=4000,
        description="近窗对话字符预算",
    )
    context_summary_every_n_messages: int = Field(
        default=12,
        description="未摘要消息数达到该阈值时刷新 conversation_summary；0 关闭",
    )

    metrics_enabled: bool = True
    span_async: bool = True

    # ---- 审计（mTLS → dbc-audit /inner/events）----
    audit_enabled: bool = True
    audit_mtls_base_url: str = Field(
        default="https://127.0.0.1:8048",
        description="审计 mTLS 地址；生产用 discovery 解析后的 https 基址",
    )
    audit_client_id: str = "dbc-askdata"

    nacos_addr: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DBC_NACOS_ADDR", "DBC_ASKDATA_NACOS_ADDR", "nacos_addr"),
    )
    nacos_register: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "DBC_ASKDATA_NACOS_REGISTER",
            "nacos_register",
        ),
    )

    @field_validator("llm_residency")
    @classmethod
    def _residency(cls, v: str) -> str:
        x = (v or "cloud").lower()
        if x not in ("local", "cloud"):
            raise ValueError("llm_residency 仅支持 local|cloud")
        return x

    def resolved_documents_dir(self) -> Path:
        raw = (self.documents_dir or "").strip()
        if raw:
            return Path(raw)
        # TODO(production): 架构概要 §6，多副本改为对象存储
        return Path(self.secrets_dir).expanduser().resolve().parent / "data" / "askdata-documents"

    def resolved_migrations_dir(self) -> Path:
        raw = (self.migrations_dir or "").strip()
        if raw:
            return Path(raw)
        # editable：src/dbc_askdata/config.py → parents[2] = 工程根
        return Path(__file__).resolve().parents[2] / "migrations"

    def jwt_secret_path(self) -> Path:
        return Path(self.secrets_dir) / "jwt-secret.txt"

    def llm_api_key_path(self) -> Path:
        return Path(self.secrets_dir) / "askdata-llm-api-key.txt"

    def resolved_llm_api_key(self) -> str:
        if self.llm_api_key.strip():
            return self.llm_api_key.strip()
        path = self.llm_api_key_path()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def resolved_llm_base_url(self) -> str:
        """与 ada-llm-core 配置互通：允许不带 /v1；HTTP 客户端需要 .../v1。"""
        u = (self.llm_base_url or "").strip().rstrip("/")
        if not u:
            return ""
        if u.endswith("/v1"):
            return u
        return f"{u}/v1"

    def assert_llm_ready(self) -> None:
        if not (self.llm_provider or "").strip():
            raise RuntimeError("未配置 DBC_ASKDATA_LLM_PROVIDER（当前为 qwen）")
        if not self.resolved_llm_base_url():
            raise RuntimeError(
                "未配置 LLM base-url（DBC_ASKDATA_LLM_BASE_URL / ADA_LLM_BASE_URL）。"
                "默认对齐 ai-dev-assistant：https://dashscope.aliyuncs.com/compatible-mode"
            )
        # 模型名可来自 provider profile；Settings 覆盖可选
        if self.llm_residency == "cloud" and not self.resolved_llm_api_key():
            raise RuntimeError(
                "residency=cloud 须配置 API Key：DBC_ASKDATA_LLM_API_KEY / ADA_LLM_API_KEY "
                "或 secrets/askdata-llm-api-key.txt"
            )

    def sample_tool_enabled(self) -> bool:
        if self.llm_residency == "cloud":
            return False
        mode = (self.sample_enabled or "auto").lower()
        if mode == "off":
            return False
        if mode == "on":
            return True
        return self.llm_residency == "local"

    def mtls_client_p12(self) -> Path:
        return Path(self.secrets_dir) / "mtls" / "clients" / f"{self.audit_client_id}.p12"

    def mtls_client_pass(self) -> Path:
        return Path(self.secrets_dir) / "mtls" / "clients" / f"{self.audit_client_id}.pass"

    def mtls_ca_cert(self) -> Path:
        return Path(self.secrets_dir) / "mtls" / "ca.crt"


@lru_cache
def get_settings() -> Settings:
    return Settings()
