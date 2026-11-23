# dbc-askdata

智能问数服务（Python / FastAPI / LangGraph ± Deep Agents）。包根：`dbc_askdata`。

## 企业级约束

- **禁止 stub LLM**：须配置可用的 OpenAI 兼容网关 + 模型。
- **默认 residency=cloud**：对齐同工作区 **ai-dev-assistant** 的 `ada.llm`（通义千问 DashScope compatible-mode / `qwen-max`）；cloud 下禁止 `sample_columns`。
- **Tool 声明制**：模型只能调用注册表 Tool，禁止直调 sqlwork HTTP。
- **审计**：本地与生产默认开启（`DBC_ASKDATA_AUDIT_ENABLED=true`），依赖 `secrets/mtls/clients/dbc-askdata.p12` + `dbc-audit` mTLS `:8048`。

## LLM（Provider Profile 插件化）

按 **`DBC_ASKDATA_LLM_PROVIDER`** 加载整套厂商包（模型档位 + 请求适配 + 提示词），目录见 `src/dbc_askdata/llm/providers/`（说明：`providers/README.md`）。

| 项 | 默认 | 环境变量 |
|---|---|---|
| provider | `qwen` | `DBC_ASKDATA_LLM_PROVIDER` / `ADA_LLM_PROVIDER` |
| residency | `cloud` | `DBC_ASKDATA_LLM_RESIDENCY` |
| base-url | 随 provider（qwen→DashScope） | `DBC_ASKDATA_LLM_BASE_URL` / `ADA_LLM_BASE_URL` |
| model（大/小） | 来自 `providers/<id>/profile.yaml` | `DBC_ASKDATA_LLM_MODEL` / `_LIGHT`（可选覆盖） |
| api-key | （cloud 必填） | `DBC_ASKDATA_LLM_API_KEY` / `ADA_LLM_API_KEY` 或 `secrets/askdata-llm-api-key.txt` |

> HTTP 客户端会把 base-url 规范为带 `/v1`。换厂商请改 `LLM_PROVIDER`，勿只改模型名。

## 本地启动

```powershell
cd e:\workspace\agent-project\database-client\dbc-askdata
# 与跑 ai-dev-assistant 相同的 Key 即可
$env:ADA_LLM_API_KEY = "sk-..."   # 或写入 secrets/askdata-llm-api-key.txt
.\scripts\run-local.cmd
```

默认以 **debugpy** 监听 `127.0.0.1:5678` 启动（可断点调试）。在 Cursor 打开「运行和调试」→ 选 **dbc-askdata: Attach** → 开始调试。

- 启动后先等 IDE 附加：`.\scripts\run-local.ps1 -WaitForDebugger`
- 不需要调试：`.\scripts\run-local.ps1 -NoDebugger`
- 热重载（与 debugpy 互斥）：`.\scripts\run-local.ps1 -NoDebugger -Reload`

仅本地 Ollama：

```powershell
$env:DBC_ASKDATA_LLM_RESIDENCY = "local"
$env:DBC_ASKDATA_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:DBC_ASKDATA_LLM_MODEL = "qwen2.5-coder"
.\scripts\run-local.cmd
```

健康检查：`http://127.0.0.1:8009/health`

## 运行配置（超管）

系统管理 → **应用配置**：左右分栏，当前可配问数 `llmProvider` / `dailyTokenLimit` / `concurrentChatLimit` / `evalTaskConcurrency`（`PUT /dbc-askdata/api/admin/app-config/askdata`）。测评用例并发在**下次启动任务**时生效。

预加载多表结构走 sqlwork `POST /meta/columns/batch` + 表知识并行；依赖 sqlwork 池与平台 PG 连接上限（见 sqlwork 设计 §连接池）。

## Docker 镜像

仓库根一键（含中间件、Java、问数、前端）：

```powershell
.\scripts\docker-deploy.cmd
.\scripts\docker-deploy.cmd -Build askdata
.\scripts\docker-deploy.cmd -Build
```

只改问数 Python：`.\scripts\docker-deploy.cmd -Build askdata`（不打 Java jar）。等价：`-RebuildImages askdata`。  
其它模块短名：`sqlwork` / `front` / `gateway` / `usercenter`（`uc`） / `manage` / `audit`（也可写 `dbc-askdata` 等全名）。多个：`-Build sqlwork askdata`。

容器内：`DBC_ASKDATA_USERCENTER_BASE_URL=http://dbc-usercenter:8004`，ada-memory 默认由 `deploy/dbc-docker.env` 的 `DBC_ASKDATA_ADA_MEMORY_BASE_URL` 注入（容器网 `http://ada-memory:8100`）。千问 Key 优先同一文件里的 `DBC_ASKDATA_LLM_API_KEY`，为空则读工作区 `secrets/askdata-llm-api-key.txt`。入口脚本把 Nacos 实例 IP 设为容器网地址。测评用例由 `init-docker-workspace.ps1` 同步到工作区 `askdata/eval-cases` 只读挂载。
