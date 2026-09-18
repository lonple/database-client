# 07 audit 详细设计

> **文档定位**：审计日志（业务操作 + SQL 操作）的落库、埋点与查询。  
> 定案依据：直写 ES、独立 `dbc-audit`、权限码可见性、含登录；**异步 HTTP 上报（不阻塞业务）**；敏感字段禁入；SQL 尽量整段原文。

---

## 1. 目标与边界

| 项 | 约定 |
| --- | --- |
| 服务 | 新建 `dbc-audit`（端口 **8008**，Gateway `/dbc-audit/**`） |
| 存储 | **仅 ES**；业务服务**不直连 ES** |
| 上报 | 经 `dbc-client` 的 **`dbc-audit-client`** → audit `/inner/events` → 写 ES |
| 发送方式 | **必须异步 HTTP**：业务线程只入队/提交异步任务，**禁止**同步等待 ingest 完成或阻塞业务返回 |
| 失败策略 | 审计失败**不阻断、不回滚**主流程；降级打应用日志（可带栈） |
| 敏感信息 | **敏感字段不得进入审计**（见 §1.1）；宁可不记该字段，不做「记了再脱敏展示」凑合 |
| 可见性 | 功能权限码 `audit.*.view`；数据范围/不可随意授权等后续再收紧（见 §2） |
| HA / 单点 | **本期不管**（单实例 audit + 本地 ES 可接受）；生产再补集群 |

前端顶栏：**审计日志**；侧栏：**业务日志**、**SQL 操作日志**。

### 1.1 敏感字段禁入（已定）

业务 `details` / SQL 上下文中，下列及同类字段**一律不采集、不序列化进 ES**：

- 密码、口令、`secretCipher`、连接凭证、私钥、JWT / refreshToken / reauthTicket  
- 可配置或注解排除：`@AuditIgnore`；client 内置名称黑名单（如 `password`、`secret*`、`*Cipher`、`token`）  
- 登录审计：只记 username + 成败，**永不记密码**  

SQL 正文尽量整段入库；若语句本身含字面量密钥，属业务 SQL 内容风险，本期不解析脱敏（后续 P1 可评估）。

---

## 2. 权限码

| code | 用途 |
| --- | --- |
| `audit.biz.view` | 业务日志列表/详情 |
| `audit.sql.view` | SQL 操作日志列表/详情 |

- 顶栏「审计日志」：持有任一 `audit.*.view`。
- 侧栏按各自 view 显隐。
- **数据范围（本人/部门等）：本期不做**，有 view 即可查列表（实现先放开）。
- **授权策略（后续）**：可改为仅固定平台角色（如 `SUPER_ADMIN` / 专用审计角色）绑定 `audit.*`，且**禁止在角色管理里随意勾选授权**（权限点标记为不可分配或角色管理 UI 隐藏）。本期种子可先绑 `SUPER_ADMIN`、`SYS_ADMIN`，不阻塞开发。

---

## 3. 事件模型

### 3.1 业务日志 `biz_op`

| 字段 | 说明 |
| --- | --- |
| eventId | UUID |
| category | 固定 `BIZ` |
| module | 如 `usercenter` / `manage` |
| action | `LOGIN` / `LOGOUT` / `CREATE` / `UPDATE` / `DELETE` / … |
| resourceType / resourceId | 资源类型与主键 |
| operatorUserId / operatorUsername | 操作人 |
| clientIp | 客户端 IP（Gateway 透传 + Filter） |
| occurredAt | 时间 |
| result | `SUCCESS` / `FAIL` |
| failReason | 失败摘要 |
| details | 见下 |
| traceId | 可选 |

**details：**

- **CREATE**：`{ "after": { "field": value, ... } }`
- **UPDATE**：`{ "changes": [ { "field", "before", "after" } ] }`
- **DELETE**：`{ "keys": { "id": 1, "name": "..." } }`
- **LOGIN** / **LOGOUT**：`{ "username", "success" }`（失败亦记；LOGIN 不含密码）

### 3.2 SQL 操作日志 `sql_op`

**粒度（已定）：一条 SQL 语句 = 一条审计文档。**  
一批多句执行会生成多条 `sql_op`（共享同一 `batchId`，用 `statementIndex` 区分）。

| 字段 | 说明 |
| --- | --- |
| eventId | UUID（每条语句独立） |
| category | 固定 `SQL` |
| batchId | 同一次批执行共享 |
| statementIndex | 句序号（从 1） |
| operatorUserId / operatorUsername | 操作用户 |
| workspaceId / workspaceName | 工作空间 |
| connectionId / connectionName | 连接 |
| dbType | 库类型 |
| occurredAt | 该句结束时间 |
| status | `SUCCESS` / `FAIL` |
| statementType | SELECT / DML / DDL / … |
| sqlText | **该句整段 SQL 原文**（非 200 字 preview；见 §5） |
| sqlTruncated | 是否因安全上限被截断（正常语句应为 false） |
| elapsedMs | 该句耗时 |
| failDetail | `denyType` / `denyObjects` / `missingOps` / `globalPolicy*` / `message` |

与 sqlwork 单句执行结果 / 鉴权失败语义对齐。

---

## 4. 低侵入埋点：`dbc-audit-client`

### 4.1 模块位置

```
dbc-client/
  dbc-audit-client/     # 新建：注解 + AOP + IngestClient
```

依赖：`dbc-client-common`（mTLS RestClient）。  
业务服务：`implementation("com.lyj.dbc:dbc-audit-client")` + 配置 audit mTLS / baseUrl。

### 4.2 业务侧「尽量只加注解」

提供：

```java
@AuditLog(
  module = "manage",
  action = AuditAction.UPDATE,      // CREATE / UPDATE / DELETE / LOGIN / CUSTOM
  resourceType = "instance",
  resourceId = "#id",                   // SpEL
  loadBefore = "getById(#id)"  // 同服务：root=当前 bean；跨 Bean 用 @xxxService.getById(#id)
)
```

- **AutoConfiguration**：注册 `AuditLogAspect` + `AuditIngestClient`（内置**异步发送器**，如专用线程池 / `CompletableFuture`，可配队列长度）。
- Aspect：环绕方法 → 取操作人/IP（MDC）→ 可选 loadBefore → 执行业务 → 组装 details（过滤敏感字段）→ **仅提交异步 HTTP**，业务方法立即返回；**禁止**在业务线程 `get()` / 同步 `exchange`。
- `@AuditIgnore` + 名称黑名单：敏感字段不进 details。
- 异步发送失败：catch 后 `log.warn("审计上报失败", e)`，**不**回传业务异常。

**能覆盖**：usercenter / manage 的增删改、登录成功/失败。  

**SQL 审计不走业务注解、不在鉴权/执行循环里散落埋点**，见 §4.4。

### 4.3 数据流

```
业务服务 @AuditLog / AuditIngestClient
    → mTLS POST dbc-audit /inner/events
        → 校验 + 规范化
        → Elasticsearch index
前端 /audit/** + JWT + audit.*.view
    → Gateway → dbc-audit 查询 API → ES search
```

业务服务与前端均**不**直连 ES。

### 4.4 SQL：管道末 Stage + 执行上下文（已定）

当前 `SqlPipeline` 为单体循环并夹杂 `sql.audit` 日志。落地时改为**显式 Stage 链**，审计作为**最后一个 Stage**，只读上下文上报：

```
Validate → Parse → Authz+Execute(逐句，结果写入 Context) → AuditStage
```

| 组件 | 职责 |
| --- | --- |
| `SqlExecuteContext` | 批次级：user、workspace、connection、batchId、dbType、clientIp；句级列表：`StatementAuditItem`（sql 全文、type、status、耗时、鉴权失败细节、执行结果摘要） |
| 鉴权/执行 Stage | **只写 Context**，不调用 audit |
| `AuditStage`（末位） | 组装事件后**异步**上报（一句一条或批量入队）；**不**等待 ES；失败不阻断已返回前端的 `ExecuteResult` |

要点：

1. **一句一条**：批 5 句成功 → 5 条 ES 文档；第 3 句鉴权失败遇错停 → 仍上报已执行的 1～2 句成功 + 第 3 句失败（后续未执行的不造空记录）。
2. **业务零埋点**：Parse/Authz/Execute 代码路径无 `AuditIngestClient`；仅 `AuditStage` 依赖 client。
3. 与现有「遇错停止」语义兼容：Context 里有什么就审计什么。
4. 实现可渐进：先抽 `SqlExecuteContext` + 末尾统一 flush；再拆独立 Stage 类。

---

## 5. SQL 正文策略（已定：尽量整段）

| 项 | 约定 |
| --- | --- |
| 存什么 | 管道解析后的**该句完整 SQL 原文**（保留换行与空白语义上的完整文本，不做业务侧截断预览） |
| 不存什么 | 不以现网 `sqlPreview`（约 200 字）作为审计正文 |
| 安全上限 | 可配置，默认 **1MB/句**；仅超过上限才截断，并置 `sqlTruncated=true` |
| UI | 列表可本地截断展示；详情展示 `sqlText` 全文（未截断时即整段） |

**原则：尽量记录整段 SQL；截断只为防异常超大脚本撑爆单文档，非常态。**

---

## 6. ES

| 项 | 约定 |
| --- | --- |
| 连接 | 仅 `dbc-audit`：`spring.elasticsearch.uris`（本地如 `http://127.0.0.1:9200`） |
| 索引 | `{env}-dbc-audit-biz-yyyy.MM`、`{env}-dbc-audit-sql-yyyy.MM` |
| 文档 _id | `eventId`（幂等重试） |
| 模板 | 启动 put composable index template（当前 `…-template-v2`，priority=300） |
| ILM | P2 |

### 6.1 映射兼容定案（强制）

| 规则 | 说明 |
| --- | --- |
| 顶层 `dynamic=false` | 只认显式字段，禁止业务涨字段污染 mapping |
| `occurredAt` | `date`，format=`strict_date_optional_time\|\|epoch_millis`；Java 侧存 **毫秒 ISO 字符串**，避免纳秒 Instant 转换失败 |
| `details` / `failDetail` | **`object` + `enabled=false`**：只进 `_source`、**不建嵌套 mapping**。UPDATE 的 `changes[].before/after` 可能是标量或对象，若开启动态嵌套会 `can't merge a non object mapping … with an object mapping` |
| 检索 | 列表筛选用顶层 keyword/text；详情抽屉读 `_source` JSON |

**映射不兼容时**：直接删旧索引 + 旧模板后重启 `dbc-audit`（开发环境接受丢审计数据）。示例：

```http
DELETE /dev-dbc-audit-biz-*
DELETE /dev-dbc-audit-sql-*
DELETE /_index_template/dev-dbc-audit-biz-template
DELETE /_index_template/dev-dbc-audit-sql-template
```

重启后会注册 `…-template-v2`。

---

## 7. API（摘要）

**Inner（mTLS）**

- `POST /inner/events`：单条或批量 ingest（`category=BIZ|SQL`）

**对外（JWT + 权限）**

- `GET /biz-logs`：筛选（时间、操作人、模块、action、result）
- `GET /biz-logs/{eventId}`
- `GET /sql-logs`：筛选（时间、操作人、workspace、connection、status、sql 关键字）
- `GET /sql-logs/{eventId}`

---

## 8. 前端

| 路由 | 说明 |
| --- | --- |
| `/audit/biz-logs` | 业务日志列表 + 详情抽屉（展示 after / changes / keys） |
| `/audit/sql-logs` | SQL 操作日志列表 + 详情（SQL、失败详情） |

模块目录：`dbc-front/src/modules/audit/`。

---

## 9. 公共上下文

- Gateway：透传 `X-Forwarded-For` / `X-Real-IP`（若尚未）。
- 各服务 Filter：解析客户端 IP + 登录用户写入 **MDC**，Aspect/SqlPipeline 只读 MDC。
- 登录失败：无 JWT 时仍记 `operatorUsername`（尝试登录名）+ IP。

---

## 10. 分期

| 阶段 | 内容 |
| --- | --- |
| P0 | `dbc-audit` + ES；`dbc-audit-client`（**异步 HTTP** + 敏感字段禁入）；SqlPipeline 接入；SQL 日志页；权限种子 |
| P0.5 | `@AuditLog` AOP；登录 + manage/usercenter 写操作；业务日志页；IP/MDC |
| P1 | 导出、可选本人范围、固定角色不可随意授权、脱敏增强 |
| P2 | 缓冲防丢、HA、ILM、bulk/背压、可观测指标、埋点 CI |

---

## 11. 方案总结（已定口径）

| 维度 | 定案 |
| --- | --- |
| 服务 | 独立 `dbc-audit`（:8008），Gateway `/dbc-audit/**` |
| 存储 | **仅 audit 写 Elasticsearch**；业务/前端不直连 ES |
| 上报 | `dbc-audit-client` → **异步** mTLS HTTP → `/inner/events`（**禁止同步阻塞业务**） |
| 业务埋点 | `@AuditLog` + AOP（含登录）；敏感字段禁入 |
| SQL 埋点 | 管道末 **AuditStage** + `SqlExecuteContext`；执行环内零埋点；异步上报 |
| SQL 粒度 | **一句一条**；同批共享 `batchId` |
| SQL 正文 | **尽量整段原文**；默认安全上限 1MB/句 |
| 敏感字段 | **不得进入审计**（黑名单 + `@AuditIgnore`） |
| 可见性 | `audit.biz.view` / `audit.sql.view`；数据范围本期不做；后续可改为固定角色且不可随意授权 |
| HA / 单点 | **本期不管** |
| 菜单 | 顶栏「审计日志」→ 侧栏「业务日志」「SQL 操作日志」 |

### 11.1 对 §12 缺口的本期处理（产品拍板）

| 原缺口 | 本期 |
| --- | --- |
| 异步导致可能丢数 | **接受**：坚持异步 HTTP，不换同步；缓冲/强一致以后再说 |
| 单点 HA | **不管** |
| 敏感字段 | **必须做**：禁入日志（不是事后脱敏凑合） |
| 权限过粗 / 可随意授权 | **先放着**；后续可固定角色 + 禁止随意勾选 |
| 留存防篡改、埋点漏标治理、性能 bulk、可观测指标等（原 5/6/7 及同类） | **先不管**，不阻塞开工 |

---

## 12. 企业级仍存问题与待补（方案后补充）

> 下列为相对「可上生产的审计中心」仍未闭合的缺口；**不否定本期方案**。  
> 产品已拍板（见 §11.1）：**单点不管**；**敏感字段本期必须禁入**；权限范围/不可随意授权后续再收；留存、埋点治理、性能 bulk 等先不管。  
> 标记：**P0 必须** / **P1 建议** / **P2 可后置** / **本期不管**。

### 12.1 完整性与可靠性

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 1 | 审计异步、失败不阻断 | ES/audit 宕机时可能**丢审计** | **本期接受**（坚持异步 HTTP）；缓冲/强一致以后再说 | **本期接受** |
| 2 | 无端到端投递确认 | 客户端以为发出、服务未落 ES 难以对账 | ingest 返回 ack；可选批量序号/水位；运维对账任务 | **本期不管** |
| 3 | 单实例 audit + 单节点 ES | 无高可用，节点故障即不可写不可查 | audit 多实例 + ES 集群（至少 3 节点生产）；健康检查与告警 | **本期不管** |
| 4 | 时钟/时区 | 多机时钟漂移导致排序混乱 | NTP；统一存 UTC，展示转本地时区 | P0 |

### 12.2 安全与合规

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 5 | SQL/业务 details 可能含敏感数据 | 密码/凭证/Token 等进 ES | **本期必须禁入**（黑名单 + `@AuditIgnore`）；不做「先记后脱敏」；身份证/手机号等增强脱敏可后置 | **P0（禁入）** |
| 6 | 审计日志可被有权用户查看/导出 | 审计员过大权限、内部泄密 | 分权：查看 vs 导出；操作审计「谁查了审计」；导出审批（可选） | **本期不管** |
| 7 | ES 访问控制弱（本地 HTTP） | 旁路直连 ES 绕过 audit 权限 | 生产强制 TLS + API Key/RBAC；网络隔离，仅 audit 可达 | **本期不管**（本地可接受） |
| 8 | IP 伪造 | 仅信客户端头可被伪造 | Gateway 覆盖/剥离不可信转发头；只信任紧邻代理追加的 XFF | P0 |
| 9 | 保留期限与不可篡改未定 | 无法满足等保/行业留存（如 6 月～3 年）；ES 可被删改 | ILM + 冷归档（对象存储）；关键索引只写别名、限制 delete；定期校验 | **本期不管** |
| 10 | 跨境/个保 | 日志含个人信息 | 最小化字段；脱敏；数据驻留策略 | **本期不管** |

### 12.3 权限与数据范围

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 11 | 本期 view 即看「全量」 | DB_ADMIN/审计员看到所有人 SQL/业务详情 | 增加数据范围：全公司 / 本部门 / 仅本人；或 `audit.sql.self.view`；后续可固定角色且不可随意授权 | **本期放着** |
| 12 | 个人空间 SQL 与公司域混存 | 个人库语句被公司审计角色看见 | 索引或字段带 `domain`/`ownerScope`；查询按域过滤 | **本期不管** |
| 13 | 无「审计查询」自身审计 | 无法追责「谁翻过敏感 SQL」 | 对 audit 查询 API 二次记 biz_op（注意递归） | **本期不管** |

### 12.4 功能覆盖与埋点质量

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 14 | `@AuditLog` 覆盖依赖人工标注 | 漏标 = 漏审计 | 清单化写接口；CI 检查关键 Controller 是否标注；或对写 Mapper 白名单兜底 | **本期不管** |
| 15 | 前后快照依赖 SpEL/`loadBefore` | 写错 SpEL → 详情为空或报错被吞 | 规范模板 + 单测；失败打 warn 指标 | P1 |
| 16 | ~~登录以外的认证事件不全~~ | 已补 LOGOUT；改密/重置/锁户等后续 | — | 部分完成 |
| 17 | 批执行中途进程崩溃 | 已执行语句可能未跑到 AuditStage | 句级先落 Context 持久化缓冲，或同步短超时写入（权衡延迟） | **本期不管** |
| 18 | 工作空间/连接名称变更 | 历史日志名称过时 | 存 id + 当时 name 快照（已规划字段）；变更不回写历史 | 已覆盖，实现时落实 |

### 12.5 性能与容量

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 19 | 高峰 SQL 一句一条写 ES | 延迟、队列堆积、ES 拒绝 | 批量 bulk；背压；限流；独立审计集群资源 | **本期不管** |
| 20 | 大 SQL（近 1MB）检索 | 索引膨胀、查询慢 | `sqlText` 不盲目分词；keyword + wildcard 策略评估；列表不回全文 | **本期不管** |
| 21 | 无限保留 | 磁盘爆满 | ILM：热→温→删/冻；按合规定保留天 | **本期不管** |
| 22 | 同步等待审计 | 若误开「强一致审计」拖垮执行 SLA | **禁止同步**；默认异步 HTTP；强一致仅白名单（本期不做） | **已定：异步** |

### 12.6 运维与可观测

| # | 问题 | 风险 | 建议 | 优先级 |
| --- | --- | --- | --- | --- |
| 23 | 缺审计链路指标 | 丢数不可见 | 指标：ingest QPS、失败数、队列深度、ES 拒绝；告警 | **本期不管** |
| 24 | TraceId 未全链路贯通 | 业务故障难关联审计 | MDC TraceId 从 Gateway 注入全服务 | P1 |
| 25 | 无演练/恢复手册 | ES 损坏后无法证明历史 | 备份快照；定期恢复演练 | **本期不管** |
| 26 | 多环境索引混用 | 测试污染生产审计 | 索引前缀带 env（`dev/staging/prod`） | P0 |

### 12.7 产品与体验（非阻塞，但企业常问）

| # | 问题 | 建议 | 优先级 |
| --- | --- | --- | --- |
| 27 | 导出、报表、合规报告 | Excel/CSV 导出 + 时间范围报表 | P1 |
| 28 | 实时尾随 / 告警订阅 | 高危 SQL、登录失败次数告警对接通知渠道 | P2 |
| 29 | 与现有「执行日志」Tab 关系 | 工作台 Tab 仍为会话态；审计中心为持久权威源；文案避免混淆 | P0（文案） |

### 12.8 本期可上线的最低企业门槛（建议）

> 产品已拍板：单点不管；留存/性能/可观测等先不管。下列仅作**日后**进严格合规生产时参考，**不阻塞本期实现**。

1. ES 集群化或书面接受单点  
2. ES 网络隔离 + 认证  
3. （敏感字段禁入 — **本期已要求实现**）  
4. IP 经 Gateway 可信传递  
5. ingest 失败可观测 + 可选磁盘缓冲  
6. 索引按环境隔离与保留策略  

---

## 13. 变更记录

| 日期 | 说明 |
| --- | --- |
| 2026-09-15 | 定案：ES 仅 audit 写；client 注解为主；权限码显隐；含登录；SQL 尽量整段（默认上限 1MB） |
| 2026-09-15 | SQL：一句一条；管道末 AuditStage + ExecuteContext，执行环内零埋点 |
| 2026-09-15 | 补充 §11 方案总结、§12 企业级缺口与生产门槛 |
| 2026-09-15 | 拍板：强制异步 HTTP；敏感字段禁入；单点不管；权限范围/不可随意授权后续再收；其余缺口先不管 |
| 2026-09-15 | P0.5：`@AuditLog` AOP 落地；usercenter 登录/用户/部门/角色；manage 实例/连接/空间/全局策略埋点 |
| 2026-09-15 | ES 映射 v2：`details`/`failDetail` enabled=false；顶层 dynamic=false；occurredAt 毫秒 ISO 字符串；补 LOGIN/LOGOUT/CRUD 场景单测 |
