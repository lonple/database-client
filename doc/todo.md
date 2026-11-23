# 问数企业级 Agent 开放能力：已做 / 待增强清单

> 依据：`dbc-askdata` 用户输入 → 生成 SQL 流程文档  
> 范围：生成止于 draft / needsHitl；不执行业务查询、不返回行数据  
> 图例：✅ 已做；🟡 部分已做 / 有限；❌ 待增强  
> 优先级：P0 开放前一票否决；P1 企业级必须；P2 体验 / 效率  
> 建议文件名：`askdata-enterprise-agent-done-todo.md`

---

## 0. 结论摘要

当前已具备企业级问数 Agent 的核心骨架：

- 生成与执行解耦；
- LangGraph 主流程清晰；
- 有找表、表意图、库通用知识、表结构、画像、关联等知识注入；
- 有 verify 机械校验 + review 语义评审；
- 有 HITL 人机协同；
- 有工具白名单与生成期探测边界；
- 有 traceId、SpanRecorder、work log 基础可观测。

开放前主要缺口（问数侧）：

- API 配额限流、幂等；
- HITL 断点续跑；
- review 失败须转 HITL（禁止放行）；
- 长期记忆统一拉取策略落地；
- 知识库/图谱依赖重试与降级策略；
- Prompt / 模型 / 工具版本化配置；
- HITL 交互告知与字段映射。

> **归属 sqlwork（不在 askdata 待办）**：细粒度权限、多租户隔离、SQL 安全、数据脱敏。  
> 问数侧仅走 sqlwork 探测/执行，由 sqlwork 统一鉴权与防护。

---

## 1. 已做清单

### 1.1 调用链与边界

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 前端 → 网关 → dbc-askdata 调用链 | `AskdataWorkbenchView` → `POST /dbc-askdata/api/chat` → StripPrefix → `POST /api/chat` | 链路清晰 |
| ✅ | 生成图入口 | `run_generate_graph` | 核心生成逻辑集中 |
| ✅ | 生成边界 | 只返回 draft / needsHitl，不执行业务查询 | 边界明确 |
| ✅ | 保存与执行分离 | `POST /api/workflows` → `POST /api/runs` → `WorkflowRunner` | 降低误执行风险 |
| ✅ | 执行行数限制 | `workflow_run_row_limit=1000` | 有基础保护 |
| ✅ | 执行开关 | `allow_user_execute=true` | 可配置 |

### 1.2 入口、鉴权、会话

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 网关路径与 StripPrefix | `Path=/dbc-askdata/**` + `StripPrefix=1` | 基础网关能力 |
| ✅ | 鉴权 | `askdata.use`；Bearer；`X-Trace-Id` | 有统一鉴权和 trace |
| ✅ | 主入口 | `POST /api/chat`，请求 `sessionId + message` | 契约简单 |
| ✅ | 响应关键字段 | `reply`、`draftId`、`hitlId`、`draft`、`needsHitl`、`route`、`traceId` | 前端可编排 |
| ✅ | HITL 恢复入口 | `POST /api/hitl/resolve` | 支持人机协同 |
| ✅ | 会话 API | `POST /api/sessions/open`、`POST /api/sessions` | 支持打开/复用/新建 |
| ✅ | session / project 归属校验 | `routes.chat` 预处理 | 基础隔离 |
| ✅ | 消息持久化 | 写 `AskMessage(role=user/assistant)` | 可追溯 |
| ✅ | work log | 清/写 work log | 有过程记录 |
| ✅ | 近窗上下文 | `load_chat_recent_turns`，`KEEP_WINDOW=10` | 有短期记忆 |
| ✅ | 已验证样本表 | `load_verified_sample_tables` | 可复用历史正确样本 |

### 1.3 LangGraph 主流程

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 主图 | `intent_gate → gather_context → fine_router → build/govern/hitl → verify → review → present` | 结构完整 |
| ✅ | CHAT / DATA 分流 | `intent_gate`：短问候启发式；否则 LLM | 有基础路由 |
| ✅ | HITL 续跑跳过闲聊 | 有 `hitl_resolution` → 直接 DATA | 恢复路径明确 |
| ✅ | 表意图 | `resolve_table_intent_query` → `entities[{entity, english}]` | 驱动找表 |
| ✅ | 多路找表 | `search_ask_catalog`：question 路 + pair 路 | 召回策略较完整 |
| ✅ | question 路 | 原句 → QUESTION 文档 → `involved_tables` | 有语义找表 |
| ✅ | pair 路 | 每对实体 → METADATA：中文 summary、英文 title、中英 fts | 有中英映射 |
| ✅ | catalog top 5 | `catalog.items[{name, description}]` | 控制上下文 |
| ✅ | 库通用知识 | `search_db_general_knowledge` → `db_general_knowledge` | 注入库级知识 |
| ✅ | 细路由 | `fine_router`：QUERY / GOVERN / HITL | 支持治理场景 |
| ✅ | 空目录强制 HITL | `route∈{QUERY,GOVERN}` 但 catalog 为空 → 未找到表 | 防止瞎编 |
| ✅ | CHAT 回复 | `chat_reply`：近窗前缀 + `CHAT_SYSTEM` | 闲聊可用 |
| ✅ | HITL 节点 | `needs_hitl=true`，`reply=hitl_question` | 可打断 |
| ✅ | QUERY 草稿 | `build_workflow_draft` | 核心生成 |
| ✅ | GOVERN 治理 | `govern_plan` → `run_deep_govern` | 支持多节点 |
| ✅ | 多节点引用 | 上游 `__node_n1__` / `FROM n1` | 支持依赖 |
| ✅ | 治理失败转 HITL | `govern_plan` 失败可转 HITL | 有兜底 |
| ✅ | 机械校验 | `verify/repair.py` → `verify_sql` | 核心质量闸门 |
| ✅ | 静态检查 | `static_check`，sqlglot，仅 SELECT/WITH | 基础安全 |
| ✅ | 等值投影检查 | `check_eq_projection` | 防止明细缺列 |
| ✅ | 码值画像校验 | `check_eq_literals_against_profiles`，必要时 `get_column_profile` | 降低码值错误 |
| ✅ | EXPLAIN 检查 | `explain_check`，多节点内联上游 | 执行前验证 |
| ✅ | 码值不确定 HITL | `needs_hitl`，清空 draft | 保守策略 |
| ✅ | 校验失败回生成 | 写 `verify_critique`，回 build/govern | 可自修复 |
| ✅ | 超轮次报错 | 超 `verify_max_regen_rounds` → `error` → present | 防死循环 |
| ✅ | 成功写回 dialect_sql | 清 critique | 输出稳定 |
| ✅ | 语义评审 | `sql_review.py` → `{ok, action: pass|regen|hitl, critique}` | 二次质量闸门 |
| ✅ | review 回生成 | regen → `review_critique` 回生成 | 有纠错 |
| ✅ | review 超限 / hitl | 转 HITL | 有兜底 |
| ✅ | present | CHAT/HITL/错误直接回复；成功 markdown 展示 SQL | 用户可确认 |
| ✅ | eval_mode | `auto_save_ready=true` | 测评可自动保存 |

### 1.4 知识、工具与上下文

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 表意图 | `table_intent.py` | 驱动找表 |
| ✅ | 找表 catalog | `ask_catalog_search.py` | 注入 build/govern |
| ✅ | 库通用知识 | `general_knowledge.py` | 用户载荷注入 |
| ✅ | 表结构 + 表知识 | `describe_table` + `search_table_knowledge` | 列名唯一来源 |
| ✅ | 列画像 | `get_column_profile` | WHERE 真实码值 |
| ✅ | 表关联 | `query_table_relations` → ada-graph | JOIN ON |
| ✅ | 会话近窗 | `load_chat_recent_turns` | CHAT 前缀 |
| ✅ | 已验证样本表 | `load_verified_sample_tables` | QUERY/GOVERN 优先考虑 |
| ✅ | 轮内压缩 | `slim_tool_result` / `fold_working_messages` | 控 token |
| ✅ | 工具网关 | `tools/gateway.py` | 统一工具入口 |
| ✅ | 工具白名单 | build/govern 禁止 `search_catalog` / `list_connections` | 防目录乱查 |
| ✅ | 强制 describe | `require_describe_tables=true` | 防瞎编列名 |
| ✅ | 生成期探测边界 | 仅允许 describe / profile / EXPLAIN，不跑业务 SELECT 出数 | 边界清晰 |
| 🟡 | 长期记忆 | `save_session_memory` 等已停用 | 能力缺失，需替代 |
| 🟡 | 事实卡 / 摘要 | 已停用 | 长会话能力弱 |

### 1.5 HITL

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 打断点 | `fine_router`、`after_router`、`govern_plan`、`verify`、`review` | 覆盖关键不确定点 |
| ✅ | 持久化 | `needs_hitl` → `AskHitl`，返回 `hitlId` | 可恢复 |
| ✅ | 恢复 API | `POST /api/hitl/resolve` → `RESOLVED`，resolution 入库 | 契约明确 |
| ✅ | 整图重跑 | 带 `hitl_resolution` 再跑 `run_generate_graph` | 实现简单 |
| ✅ | 跳过闲聊 | `intent_gate` 有 `hitl_resolution` 直接 DATA | 恢复路径短 |
| ✅ | 路由恢复 | `fine_router` 用 `resolution.route` | 尊重用户选择 |
| ✅ | 提示词注入 | `hitl_for_sql_prompt`：码值/口径 → `text`；物理表名 → `confirmed_table` | 信息进入生成 |
| ✅ | 确认卡片 | resolve → `ask_hitl_card`；有用归并 INTENT_TABLE / METADATA 字段字典 | 见落地计划 §3.1 |
| 🟡 | 断点续跑 | 当前是整图重跑，非断点续跑 | 成本与幂等风险 |

### 1.6 配置与可观测

| 状态 | 已做项 | 文档依据 | 评价 |
|---|---|---|---|
| ✅ | 工具轮次 | `llm_max_tool_rounds=8` | 有限制 |
| ✅ | 校验回生成 | `verify_max_regen_rounds=2` | 有限制 |
| ✅ | 遗留盲修 | `verify_max_repair_rounds=3`，主路径不用 | 已识别 |
| ✅ | 语义评审回写 | `sql_review_max_regen=1` | 偏保守 |
| ✅ | 知识检索 | `ada_memory_base_url` :8100 / `dbc产品` | 外部依赖 |
| ✅ | 表关联 | `ada_graph_base_url` :8102 | 外部依赖 |
| ✅ | 用户执行 | `allow_user_execute=true` | 可关 |
| ✅ | 执行行限 | `workflow_run_row_limit=1000` | 基础保护 |
| ✅ | tool 结果瘦身 | `context_tool_result_max_chars=4000` | 控上下文 |
| ✅ | 轮内折叠 | `context_working_budget_chars=48000` | 控 token |
| ✅ | 治理步数 | `deep_agent_max_steps=6` | 有限制 |
| ✅ | trace | `X-Trace-Id`、`SpanRecorder`、work log | 有基础可观测 |

---

## 2. 待增强清单

### 2.1 P0：开放前一票否决

#### 2.1.0 归属 sqlwork（本期不在 askdata 落地）

| 能力 | 处理方 | 说明 |
|---|---|---|
| 细粒度权限 | sqlwork | 表/库/schema 鉴权、`ObjectFilter`、语句授权 |
| 多租户隔离 | sqlwork | 连接与对象可见性隔离 |
| SQL 安全 | sqlwork | DDL/DML、全局策略、危险语句拦截 |
| 数据脱敏 | sqlwork | 结果/列脱敏等（执行与探测出口统一处理） |

问数 `static_check` / 工具白名单仍保留为生成期辅助闸门，**不以 askdata 替代 sqlwork 安全边界**。

#### 2.1.1 问数侧仍须落地

| 优先级 | 能力 | 现状 / 缺口 | 建议增强 | 验收标准 |
|---|---|---|---|---|
| P0 | API 配额限流 | 未见按用户日限额 | **按登录用户日累计 LLM token**；超配置阈值 → 429；**测评不计/不拦/不展示额度** | 超限 429；测评路径零额度副作用 |
| P0 | 幂等 | HITL 非 PENDING→400；chat 无幂等键 | `Idempotency-Key`；重复 resolve 去重；重复草稿控制 | 同一 HITL 重复 resolve 只产生一个结果 |
| P0 | HITL 断点续跑 | 整图重跑，非断点续跑 | 检查点、状态恢复、工具结果缓存、防重复工具调用 | 恢复不重复 describe/profile；无重复 AskHitl |
| P0 | Review 失败转 HITL | LLM/解析失败 → **放行 pass**（反模式） | 空/解析失败/未知 action → `action=hitl`；禁止可执行 draft | review 异常绝不自动进入可保存/执行状态 |

### 2.2 P1：企业级必须（本期拍板）

| 优先级 | 能力 | 现状 / 缺口 | 拍板方案 | 验收标准 |
|---|---|---|---|---|
| P1 | 长期记忆（统一近窗） | CHAT 注入近窗原文；QUERY/GOVERN 注入已验证样本表；二者拉取策略不一致 | **统一拉取 10 条**；闲聊带近窗对话；问数带入形态为 **问题 + 对应表**（`{question, tables}`） | CHAT/QUERY 均近窗 10；问数载荷为问题+表，非全文对话 |
| P1 | 知识库 / 图谱依赖 | Client 仅 timeout，无统一重试 | **知识库**：失败重试 1 次，仍失败 → **HITL**；**图谱**：重试失败后 **忽略**（不阻断），**业务日志必记（带栈）** | memory 挂掉可 HITL；graph 挂掉可继续且日志可查 |
| P1 | Prompt / 模型 / 工具版本 | prompt 写死代码；模型仅 Settings 静态项 | **管理配置 + 版本维护**；运行时读当前生效版本；切换配置则全链路切换 | 改配置即可切换；可回滚上一版本 |
| P1 | HITL 体验与映射 | 前端自由文本「补充码值/口径」；`options` 几乎只有原问题 | 每次 HITL **告知要补充什么**；后端契约（`kind`/`fields`/`candidates`）；前端按契约渲染；resolve 按映射进 `hitl_confirmation` | 用户不猜填；码值/表名/口径分槽；生成侧映射正确 |
| P1 | 性能成本 | 有压缩/画像缓存/轮次上限；HITL 整图重跑贵 | 见 §2.2.1；优先断点续跑 + 工具缓存 | 续跑 token/时延可度量下降 |

#### 2.2.1 性能成本：可优化空间

**已有**：`slim_tool_result`、`fold_working_messages`、找表 pair `asyncio.gather`、列画像 cache+TTL、各轮次上限。

**高价值（优先）**

| # | 机会 | 现状问题 | 预期收益 |
|---|---|---|---|
| 1 | HITL 断点续跑 + 工具结果缓存 | 续跑整图重跑，intent/gather/describe/profile 重复 | **最大**：续跑时延与 token |
| 2 | gather 阶段并行 | 表意图→找表→库通用知识偏串行 | 中：首包时延 |
| 3 | describe/catalog 会话级缓存 | HITL/regen 重复 describe | 中高：工具轮与 sqlwork 压力 |
| 4 | LLM 分级 | 门闩/细路由与生成同级模型 | 中：成本（需评测门禁） |
| 5 | verify 画像预取合并 | 多列逐次 profile | 中：校验时延 |

**收益有限 / 后置**：再压压缩预算、砍 GOVERN 步数、跨会话全局缓存。

**结论**：具备明显可优化空间；**第一优先 = P0 断点续跑 + describe/profile 缓存**。

### 2.3 P2：体验与效率（后置）

| 优先级 | 能力 | 现状 / 缺口 | 建议增强 | 验收标准 |
|---|---|---|---|---|
| P2 | 多轮修正 | 主要整图重跑 | 局部重生成、节点编辑、SQL diff、版本 | 用户可小步修正 |
| P2 | 复杂分析 | 支持 GOVERN 多节点 | 窗口函数、CTE、物化、性能提示、查询重写 | 复杂问句采纳率提升 |
| P2 | 开放生态 | 无 | SDK、Webhook、事件、沙箱、示例、插件 | 第三方可接入 |
| P2 | 多语言 / 时区 / 口径 | 未明确 | 中英文、时区、币种、日期口径 | 跨区域可用 |
| P2 | 运营指标 | 未明确 | 草稿保存率、执行确认率、用户修正率、HITL 解决时长 | 可持续运营 |
| P2 | 可解释性 | 主要给 SQL | 找表/JOIN/口径/校验结构化展示 | 用户能理解为什么这么查 |
| P2 | 监控告警 / OpenAPI | 有 metrics/监控页；无告警与契约版本 | SLA 告警；OpenAPI/错误码 | 可运维、可对接 |

---

## 3. 建议路线图

### 开放前必须完成（askdata）
1. API 配额、限流、幂等；
2. HITL 断点续跑（含工具结果缓存）；
3. Review 失败转 HITL（禁止放行）。

> 权限 / 多租户 / SQL 安全 / 脱敏 → **sqlwork**，不列入 askdata 开放门禁。

### 企业级必须补齐（本期拍板）
1. 长期记忆统一：近窗 10；问数注入「问题 + 表」；
2. 知识库重试 1 次否则 HITL；图谱重试失败忽略 + 业务日志；
3. Prompt / 模型 / 工具版本化管理配置；
4. HITL 告知补充项 + 前后端字段映射；
5. 性能：断点续跑 / 工具缓存 / 可并行与模型分级（见 §2.2.1）。

### 体验与效率（后置）
1. 多轮局部修正；
2. 可解释性增强；
3. 开放 SDK / Webhook；
4. 运营 KPI。

---

## 4. 验收门禁建议

| 指标 | 建议门禁 | 是否一票否决 | 归属 |
|---|---|---|---|
| 越权拦截 | 100% | 是 | sqlwork |
| 敏感数据泄露 | 0 | 是 | sqlwork |
| DDL / DML / 危险语句拦截 | 100% | 是 | sqlwork |
| Review 异常自动放行 | 0 | 是 | askdata |
| HITL 重复 resolve 去重 | 100% | 是 | askdata |
| API 超限返回 429 | 100% | 是 | askdata/网关 |
| 知识库失败（重试后）转 HITL | 100% | 是 | askdata |
| 图谱失败可降级继续 | 100% | 否 | askdata |
| HITL 恢复成功率 | ≥ 95% | 否 | askdata |
| 找表 Recall@5 | ≥ 90% | 否 | askdata |
| EXPLAIN 通过率 | ≥ 95% | 否 | askdata |
| 人工采纳率 | ≥ 85% | 否 | askdata |
| P95 / 单次 token | 按业务/租户 | 否 | askdata |

---

## 5. 关键文件映射

| 职责 | 路径 |
|---|---|
| Chat / HITL / Runs API | `dbc-askdata/src/dbc_askdata/api/routes.py` |
| 生成图 | `.../graph/generate.py` |
| Tool Agent | `.../graph/tool_agent.py` |
| 治理生成 | `.../graph/deep_govern.py` |
| 语义评审 | `.../graph/sql_review.py` |
| HITL → 提示词 | `.../graph/hitl_prompt.py` |
| 校验 | `.../verify/repair.py` |
| 找表 / 意图 / 通用知识 | `.../knowledge/ask_catalog_search.py`、`table_intent.py`、`general_knowledge.py` |
| 会话上下文 | `.../context/session_context.py`、`compress.py` |
| Tools | `.../tools/gateway.py` |
| 执行器 | `.../workflow/runner.py` |
| 前端 | `dbc-front/.../api/askdata.ts`、`AskdataWorkbenchView.vue` |

---

## 6. 一句话总结

已做的是“能生成、能校验、能评审、能 HITL、边界清晰”；  
问数开放前要补的是“限流幂等、断点续跑、Review 不放行”；  
企业级再补“统一近窗记忆、依赖重试策略、版本化配置、HITL 可填可映射、续跑成本”；  
权限/隔离/SQL 安全/脱敏归 **sqlwork**。