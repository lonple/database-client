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

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres",
        description="平台库 DSN（asyncpg）",
    )
    database_schema: str = "askdata"

    sqlwork_base_url: str = Field(default="http://127.0.0.1:8007")
    sqlwork_timeout_seconds: float = 60.0
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

    # ---- LLM（对齐 ai-dev-assistant / ada.llm：默认云端 DashScope compatible-mode）----
    llm_residency: str = Field(default="cloud", description="local | cloud")
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode",
        description="OpenAI 兼容根（可无 /v1；客户端会规范为 .../v1）。与 ada.llm.base-url 一致",
        validation_alias=AliasChoices(
            "DBC_ASKDATA_LLM_BASE_URL",
            "ADA_LLM_BASE_URL",
            "llm_base_url",
        ),
    )
    llm_model: str = Field(
        default="qwen-max",
        description="与 ada.llm.chat-model 默认一致",
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

    sample_enabled: str = "auto"  # auto：仅 local 开启；cloud 强制关闭
    sample_max_columns: int = 5
    sample_max_rows: int = 30

    # 列画像 / 枚举探测（模型按需触发 get_column_profile）
    profile_cache_ttl_seconds: int = 3600
    profile_enum_max_distinct: int = 64
    profile_enum_top_n: int = 30

    verify_max_repair_rounds: int = 3
    workflow_run_row_limit: int = 1000
    allow_user_execute: bool = True
    temp_table_prefix: str = "askdata_tmp_"
    result_table_prefix: str = "askdata_rst_"
    rerun_cleanup: str = "drop_then_recreate"

    deep_agent_max_steps: int = 6

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
        if not self.resolved_llm_base_url():
            raise RuntimeError(
                "未配置 LLM base-url（DBC_ASKDATA_LLM_BASE_URL / ADA_LLM_BASE_URL）。"
                "默认对齐 ai-dev-assistant：https://dashscope.aliyuncs.com/compatible-mode"
            )
        if not (self.llm_model or "").strip():
            raise RuntimeError("未配置 DBC_ASKDATA_LLM_MODEL / ADA_LLM_CHAT_MODEL")
        if self.llm_residency == "cloud" and not self.resolved_llm_api_key():
            raise RuntimeError(
                "residency=cloud 须配置 API Key：DBC_ASKDATA_LLM_API_KEY / ADA_LLM_API_KEY "
                "或 secrets/askdata-llm-api-key.txt（与 ai-dev-assistant 通义千问 Key 相同）"
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
