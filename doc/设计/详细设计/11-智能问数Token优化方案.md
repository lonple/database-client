# 智能问数 Token 优化方案

| 项 | 内容 |
|---|---|
| 状态 | 方案定稿，待按优先级落地 |
| 范围 | `dbc-askdata` 问数主链路（CHAT / QUERY / GOVERN / HITL） |
| 关联 | `08-智能问数详细设计.md`；`doc/todo.md` §2.2.1 |
| 模型约定 | 由 `DBC_ASKDATA_LLM_PROVIDER` 加载 Provider Profile（当前仅 `qwen`：flash+max）；**不用** `qwen-plus` / 已下线 `qwen-turbo` |

---

## 1. 目标

在**不牺牲选表/SQL 正确率底线**的前提下：

1. 降低单次问数 **输入 Token**（主因）与总 Token；
2. 降低 HITL / 评审重写后的 **重复消耗**；
3. 可用监控量化：`ask_turn.token_*`、LLM span 的 `tokenIn` / 轮次数。

**原则**：省 Token ≈ **少让大模型多轮写 SQL** + **少往上下文塞长文本** + **少整图重跑**。再拧压缩参数收益有限。

---

## 2. Token 花在哪（白话）

典型查数问句（如「各部门在职人数」）：

| 步骤 | 模型 | Token 量级 | 说明 |
|------|------|------------|------|
| 意图门闩 | flash | 少 | 短 JSON |
| 实体抽取 / 细路由 | flash | 少 | 短 JSON |
| **写 SQL（tool_agent 多轮）** | **max** | **最大** | 每轮重发：系统提示 + tools schema + 历史探测结果 |
| 语义评审 | flash | 中 | 再读一遍 SQL + 上下文 |
| 校验失败修复 / 评审打回重写 | max | 再翻倍 | 等价再跑一轮 build |

输入 Token 远大于输出。大头在 **build / govern 的多轮 LLM**，不在门闩。

---

## 3. 已具备能力（基线）

以下已落地，**不必再作为第一优先**：

| 能力 | 位置 / 配置 | 作用 |
|------|-------------|------|
| 模型分级 | `llm_model=qwen-max`，`llm_model_light=qwen3.6-flash` | 门闩/实体/路由/review 用小模型 |
| 工具结果瘦身 | `slim_tool_result`，`context_tool_result_max_chars=4000` | describe/profile 不灌全量 |
| 轮内折叠 | `fold_working_messages`，预算约 48k 字符 | 超限折叠早期 tool 轮 |
| Redis 工具缓存 | describe / profile / 库通用知识 / ask_catalog | 同键二次命中降下游与时延 |
| 目录裁剪 | catalog top5，仅 name+description | gather 后注入体积可控 |
| 近窗截断 | 会话近窗条数/字符上限 | 跨轮注入可控 |
| Span 可观测 | `llmRounds` + turn token | 用于验收优化效果 |

---

## 4. 优化项（按优先级）

### 4.1 P0-1：HITL / 重写断点续跑（收益最大）

**问题**：人工确认或评审/校验打回后，易从意图门闩整图重跑，intent / gather / describe / profile 重复计费。

**方案**：

- 图状态检查点（已有雏形则补齐）：记录已完成节点、catalog、已 describe 表、画像、draft；
- resolve / regen 从断点恢复，**跳过**已成功节点；
- 与 Redis / 会话级工具缓存配合，禁止重复探测同一表。

**验收**：

- 同会话 HITL 续跑：不再出现完整的 intent_gate → gather → 全量 describe 链路；
- 该 turn 的 `tokenTotal` 相对「整图重跑」可度量下降（建议对比用例固化）。

---

### 4.2 P0-2：减少 build 轮次（少调大模型）

**问题**：每多一轮 tool_call，下一轮要把工具结果再读进大模型 → **一轮探测 ≈ 再烧一轮输入 Token**。

**方案**：

1. **细路由选表 + 服务端预 describe（已落地）**：`fine_router` 在输出 `route` 同时给出 `recommended_tables`；路由为 QUERY/GOVERN 时对推荐表并行 `describe_table`，写入 `pre_described_tables` / `described_columns`。`build_workflow_draft` / `govern_plan` 将 `recommended_tables`+`described_tables` 注入 user 上下文；提示词禁止对已描述表再调工具；`tool_agent` 以 `described_columns` 种子化已探集合，误调 `describe_table` 时短路返回 `already_in_context`。
2. **画像按需**：仅当 WHERE/分组依赖离散码值时才允许 `get_column_profile`；禁止顺手多探。
3. **会话内已探表**：已 describe 的列名清单注入上下文，折叠后仍可避免重探；检查点持久化 `recommended_tables` / `pre_described_tables`。

**验收**：

- 简单单表问句：build 父 span `llmRoundCount` 下降（目标：常见路径少 1～2 轮）；
- 对应 LLM span 的 `tokenIn` 总和下降。

---

### 4.3 P1-1：可跳过的 LLM 跳过

**问题**：简单路径也完整走细路由 + 评审。

**方案**：

- 短问候 / 模板回复：继续启发式，零 LLM（已有则可扩展词表）；
- 简单单表 + verify 已通过：允许 **跳过 review**，或仅规则评审；
- ~~可选：门闩与实体抽取合并为一次 flash 调用~~ **已落地**：`intent_gate` 一次返回 `gate`+`entities`，`gather_context` 复用，不再二次抽取（HITL 缺实体时仍可回退补抽）。

**验收**：简单问句少一次 review（或少一次 light 调用）；测评集回归不掉点。DATA 路径监控中不应再出现独立的 `table_intent` LLM span（可为 skipped GRAPH）。

---

### 4.4 P1-2：缩短灌进大模型的文本

**问题**：通用知识全文、过长 `BUILD_SYSTEM`、完整 tools 描述，在 **每一轮** build 中重复计费。

**方案**：

- `db_general_knowledge`：只注入摘要/要点，不灌全文 body；
- System 提示模块化：无 JOIN 不塞关联段；无码值场景不塞画像规则；
- tools schema：阶段已 exclude 的工具保持关闭；必要工具的 description 精简。

**验收**：单轮 build 的 `tokenIn` 中位数下降；正确率评测持平或可接受波动。

---

### 4.5 P2：后置 / 收益有限

| 项 | 说明 |
|----|------|
| 再压 `context_working_budget_chars` | 边际收益小，过紧易丢关键列信息 |
| 跨会话全局 prompt/结果缓存 | 复杂度高，口径变更风险 |
| 砍 GOVERN 最大步数 | 复杂题质量可能下降，需单独评测 |
| 会话摘要替代近窗原文 | 配置位已有，需质量门禁后再开 |

---

## 5. 优先级总览

```
高 ─► ① 断点续跑 / 禁止整图重跑
      ② 预 describe + 少探画像（少轮次）
      ③ 简单路径跳过 review / 合并 light 调用
      ④ 缩短 system / 知识 / tools 文案
低 ─► ⑤ 再抠压缩预算、全局缓存、砍 GOVERN 步数
```

**推荐落地顺序**：先做 ① + ②，用监控对比同一批问句；再视数据做 ③④。

---

## 6. 度量与验收方法

1. **问数列表**：对比优化前后同问句的 `tokenTotal`、`latencyMs`。
2. **Span 详情**：
   - build / govern 父节点 `llmRoundCount`；
   - 各 LLM 子 span 的 `tokenIn` / `tokenOut`；
   - `payloadMeta.cache`（hit/set）确认缓存是否命中。
3. **建议基线用例**：固定 3 类——单表聚合、需码值过滤、HITL 补表名后续跑。

通过标准（建议）：

| 场景 | 目标（相对当前基线） |
|------|----------------------|
| 单表简单查询首轮 | build 轮次 ↓，总 token ↓ ≥ 15%（经验值，落地后校准） |
| HITL 续跑 | token ↓ ≥ 40%（相对整图重跑） |
| 测评集 | 通过率不回退（或回退在约定阈值内） |

---

## 7. 风险与约束

- 预 describe 选错表会浪费一轮：须基于 catalog topK 与实体对齐，失败可回退模型自探。
- 跳过 review 仅限低风险路径，复杂 GOVERN / 多表 JOIN 默认保留。
- `qwen3.6-flash` 默认开启思考链时，单次门闩可刷出数百～上千 output token、耗时 7～10s；**调用须传 `enable_thinking=false`**（`LlmClient` 已默认关闭），只取 `content`。
- 企业级：禁止为省 Token 关闭鉴权、缓存用户敏感全量样本进 Redis 无 TTL；缓存键须含 connection/db/schema。

---

## 8. 非目标

- 不改为「本地假 LLM」或跳过生产校验。
- 不把日配额（当前默认 50 万 token/用户/日）当作优化手段本身；配额是护栏，优化是降低真实消耗。
- 不在本方案内改前端交互文案（除非 HITL 断点契约需要字段）。

---

## 9. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-10-14 | 初稿：基于现状基线与 Token 花销分析整理优先级 |
