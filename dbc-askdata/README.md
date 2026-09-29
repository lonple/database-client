# dbc-askdata

智能问数服务（Python / FastAPI / LangGraph ± Deep Agents）。包根：`dbc_askdata`。

## 企业级约束

- **禁止 stub LLM**：须配置可用的 OpenAI 兼容网关 + 模型。
- **默认 residency=cloud**：对齐同工作区 **ai-dev-assistant** 的 `ada.llm`（通义千问 DashScope compatible-mode / `qwen-max`）；cloud 下禁止 `sample_columns`。
- **Tool 声明制**：模型只能调用注册表 Tool，禁止直调 sqlwork HTTP。
- **审计**：本地与生产默认开启（`DBC_ASKDATA_AUDIT_ENABLED=true`），依赖 `secrets/mtls/clients/dbc-askdata.p12` + `dbc-audit` mTLS `:8048`。

## LLM 默认（与 ai-dev-assistant 一致）

| 项 | 默认 | 环境变量（DBC / ADA 互通） |
|---|---|---|
| residency | `cloud` | `DBC_ASKDATA_LLM_RESIDENCY` |
| base-url | `https://dashscope.aliyuncs.com/compatible-mode` | `DBC_ASKDATA_LLM_BASE_URL` / `ADA_LLM_BASE_URL` |
| model | `qwen-max` | `DBC_ASKDATA_LLM_MODEL` / `ADA_LLM_CHAT_MODEL` |
| api-key | （必填） | `DBC_ASKDATA_LLM_API_KEY` / `ADA_LLM_API_KEY` 或 `secrets/askdata-llm-api-key.txt` |

> HTTP 客户端会把 base-url 规范为带 `/v1`（与 Spring AI 拼路径方式对齐）。

## 本地启动

```powershell
cd e:\workspace\database-client\dbc-askdata
# 与跑 ai-dev-assistant 相同的 Key 即可
$env:ADA_LLM_API_KEY = "sk-..."   # 或写入 secrets/askdata-llm-api-key.txt
.\scripts\run-local.cmd
```

仅本地 Ollama：

```powershell
$env:DBC_ASKDATA_LLM_RESIDENCY = "local"
$env:DBC_ASKDATA_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:DBC_ASKDATA_LLM_MODEL = "qwen2.5-coder"
.\scripts\run-local.cmd
```

健康检查：`http://127.0.0.1:8009/health`
