# 详细设计：SQL 工作台（sqlwork）

> **服务**：`dbc-sqlwork`  
> **包根**：`com.lyj.dbc.sqlwork`  
> **对外前缀**：`/dbc-sqlwork/**`（经 Gateway `StripPrefix=1`）  
> **状态**：已定详细设计；骨架与执行/元数据/鉴权联调链路已落地代码（前端 sqlwork 页与完整工作空间 UI 后续）。  
> **关联**：[需求设计](../需求/01-需求设计.md)、[架构设计](../架构/01-架构设计.md)、[manage 详设](./02-manage详细设计.md)、[服务间请求签名](./04-服务间请求签名.md)、[网关与注册中心](./05-网关与注册中心.md)、[前端与界面设计](./06-前端与界面设计.md)

> **本期目标**：包结构清晰；批执行 SQL 与多结果/执行日志；会话窗口与手动事务；元数据供工作空间与对象树。  
> **方言**：先落地 **PostgreSQL**；业务路径只依赖 `DbDialect` SPI。  
> **鉴权**：每次元数据与执行均校验工作空间授权；再套 **全局管控策略**（经 manage）。**无** Risk/高危步骤。  
> **执行**：支持多语句（Druid 拆分，遇错停）；默认自动提交；手动模式需用户 `BEGIN` 后租约连接。默认最多 **1000** 行/结果集（可配）。  
> **选型摘要**：动态连接池（Druid）、SQL 解析（Druid SQL Parser）见 [架构设计](../架构/01-架构设计.md) §1.3。

---

## 1. 定位与边界

| 做 | 不做（本期） |
| --- | --- |
| 目标库 **唯一出口**：元数据、执行 SQL、返回结果集 | 持有连接密码明文长期存储（密码在 manage） |
| 动态连接池（按 connectionId） | 脚本仓库 / 异步导出 / WS |
| 方言：先 **PostgreSQL**；`DbDialect` SPI，MySQL 可插拔接入 | 在业务代码里写死 `if (pg) … else if (mysql)` |
| 调 manage：**鉴权 + 凭证 + 我的空间/可用连接（inner）** | 浏览器直连目标库 |
| 供 manage / 前端的元数据 API | 审计服务完整落地（先日志） |

### 1.1 协作

```
前端
  ├─ /dbc-sqlwork/**   对象树、执行、结果；（可选）聚合后的「我的空间/可用连接」
  └─ /dbc-manage/**    工作空间 CRUD、资产/成员授权

sqlwork 出站（mTLS inner → manage）：
  - 鉴权裁决（成员 / 资产 / SQL 操作）
  - 连接凭证（解密后仅内存）
  - 我的工作空间列表、空间下我可用的连接

工作空间「指定表」选表：方案 A
  前端 → manage（校验 data-scope）
       → manage mTLS → sqlwork `/inner/meta/**`（只查库）
       → 回传前端

SQL 工作台对象树 / 执行元数据：
  前端 → sqlwork `/meta/**`（sqlwork 调 manage 按成员授权过滤）

执行：
  前端 → Gateway → sqlwork.api
       → pipeline（Parse 批 → 空间 Authz → 全局策略 → Execute）
       → runtime（池 或 会话租约连接）
       → 多结果 + 逐句执行日志
```

### 1.2 方言扩展约定（反 if 堆砌）

- 注册表：`DialectRegistry` 按 `DbType` → `DbDialect` 实现。
- **所有**切库、探活、标识符引用、元数据 JDBC/SQL、类型名映射，只进 `DbDialect`（及 runtime.meta 对 dialect 的调用）。
- `pipeline` / `api` / `AuthzClient` **不出现**库类型分支；新增 MySQL = 新 `MysqlDialect` + 注册，不改执行主路径。

---

## 2. 工程与模块划分

| 项 | 约定 |
| --- | --- |
| 工程目录 | `dbc-sqlwork` |
| 包根 | `com.lyj.dbc.sqlwork` |
| 端口 | `8007`（接 8006 manage） |
| Nacos | `dbc-sqlwork` |
| Gateway | `Path=/dbc-sqlwork/**` + `StripPrefix=1` |
| 平台库 | 可选：本期若无可持久化状态，**可不建 schema**；会话/Tab 状态先前端本地。若需执行历史再加 `sqlwork` schema |
| 密钥 | 同仓库根 `secrets/`；登记 usercenter 应用 `dbc-sqlwork` + mTLS 客户端证 |

### 2.1 包结构（与规划一致，略作落地拆分）

```
com.lyj.dbc.sqlwork
  SqlworkApplication
  api/                 # 对前端 HTTP
    MetaController
    ExecuteController
    WorkspaceConnController   # 当前空间下「我可用的连接」列表（可调 manage 或聚合）
  dialect/             # SPI
    DbDialect
    PostgresDialect
    MysqlDialect          # 按确认是否本期实现
    DialectRegistry
  runtime/
    pool/                 # 按 connectionId 的 Druid 池缓存、淘汰、启停
    jdbc/                 # 执行、结果截断、类型映射
    meta/                 # 元数据查询（库/模式/表/视图）
  pipeline/
    SqlPipeline           # 批 Parse → 空间鉴权 → 全局策略 → Execute
    SqlParseService       # Druid：拆分多语句、类型、表引用
    SqlSessionManager     # 会话窗口、BEGIN 租约、闲置清理
    AuthzClient           # 调 manage inner
  client/
    ManageInnerClient     # mTLS：凭证、鉴权
  security/               # JWT 与 usercenter 同密钥校验
  common/                 # ApiResponse、异常、GlobalExceptionHandler（打栈）
  config/
```

| 模块 | 职责 | 禁止 |
| --- | --- | --- |
| **api** | DTO/VO、参数校验、编排 | 直接 JDBC、解析权限规则 |
| **dialect** | 探活 SQL、切库、标识符引用、元数据 SQL/JDBC DatabaseMetaData 差异 | 业务鉴权 |
| **runtime** | 池、执行、元数据原始查询 | 解释工作空间授权语义 |
| **pipeline** | 解析、调鉴权、组装执行请求 | 持有密码落盘 |
| **client** | 与 manage / usercenter 出站 | — |

---

## 3. 核心领域对象（内存/API，非平台表）

| 概念 | 说明 |
| --- | --- |
| `connectionId` | manage 侧连接主键；建池键 |
| `workspaceId` | 当前工作空间；执行与元数据必带 |
| `DbType` | `POSTGRESQL` / `MYSQL` / … 与 manage asset 枚举一致 |
| `ObjectRef` | `catalog/database` + `schema`(可空) + `name` + `type(TABLE\|VIEW)` |
| `SqlOp` | `SELECT/INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/TRUNCATE/...` 与授权勾选对齐 |
| `ExecuteRequest` | workspaceId, connectionId, sql, maxRows?, timeoutMs? |
| `ExecuteResult` | columns[], rows[][], rowCount, truncated, elapsedMs, statementType, message |

---

## 4. 对外 API（前端，经 Gateway `/dbc-sqlwork`）

统一：JWT；`ApiResponse`；错误不回传栈。

### 4.1 工作台上下文

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/workspaces/mine` | 我加入的工作空间列表（或前端改调 manage；二选一见 §11） |
| GET | `/workspaces/{workspaceId}/my-authz` | 当前用户在该空间的角色与可访问资产/权限（选空间页右侧） |
| GET | `/workspaces/{workspaceId}/connections` | 当前用户在该空间下 **已成员授权** 的连接摘要（id/name/dbType） |

### 4.2 元数据（对象树 + 工作空间选表）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/databases` | query: `workspaceId`, `connectionId` → 库列表 |
| GET | `/meta/schemas` | PG：`database` → schema 列表；MySQL：可空或返回与 library 同层约定 |
| GET | `/meta/tables` | 分页：`workspaceId, connectionId, database, schema?, keyword?, page, size`；含 `objectType=TABLE\|VIEW` 或分接口 |
| GET | `/meta/tree` | 可选：一次拉浅树（库→…）供工作台左侧；大数据量时前端改懒加载调上面三个 |

**过滤规则（定案）：**

- 必须带 `workspaceId`；`purpose=WORKBENCH`：成员 + 连接已授权且 **具备任意 SQL 操作权限** 即可浏览（不要求 SELECT）。
- 返回对象 ⊆ 成员授权并集：连接级全量；否则按 DATABASE / SCHEMA / TABLE 范围裁剪库、模式、表/视图。
- 裁决结果带 `objectFilter`（`unrestricted` 或 `scopes[]`）；sqlwork `/meta/**` 据此过滤。执行仍走 `purpose=EXECUTE` 校验具体 op/表。
- 资产授权选表场景：调用方为管理员配空间资产时，需 **更宽** 的可见性（data-scope 连接上的全表列表）——见 §5.2 / §11。

**性能（大资产）：**

| 授权形态 | 策略 |
| --- | --- |
| 连接级 / 库级 / 模式级 | 按请求的 database/schema **正常分页**查目标库；不在内存二次裁剪表页 |
| 仅表级白名单 | **不下扫全 schema**：方言 `table_name IN (...)` 下推；分页 total 正确，避免「先 page 再滤导致漏页」 |
| 库/模式名可从授权推导 | **跳过 catalog 全量列举**，直接返回授权中的库/模式名（懒加载树主路径） |
| `/meta/tree` | 同样先规划再查，禁止先拉整库浅树再过滤 |

### 4.3 执行

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/execute` | body: workspaceId, connectionId, sql, sessionId?, maxRows?, database?, schema?, reauthTicket? |
| POST | `/sessions` | 创建/保活会话窗口元数据 |
| POST | `/sessions/{id}/heartbeat` | 活跃心跳 |
| DELETE | `/sessions/{id}` | 关闭：事务中则 rollback 并释放租约 |
| POST | `/execute/cancel` | 可 stub（依赖超时） |

**批执行响应 `data` 示例：**

```json
{
  "sessionId": "…",
  "stopped": false,
  "statements": [
    {
      "index": 0,
      "sql": "SELECT 1",
      "statementType": "SELECT",
      "success": true,
      "logLevel": "INFO",
      "message": null,
      "policyAction": "NONE",
      "result": { "columns": [...], "rows": [...], "rowCount": 1, "truncated": false }
    }
  ]
}
```

- 多个成功 SELECT：前端下方多个结果 Tab。  
- `logLevel`：`INFO` / `WARN`（告警标红）/ `ERROR`（无权限、阻断、二次鉴权失败、执行失败）。  
- `policyAction`：`NONE` \| `BLOCK` \| `ALERT` \| `REAUTH`。

### 4.4 探活（可选）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/connections/{id}/ping` | 短超时探活；供已落库连接测试 |
| POST | `/inner/connections/ping` | manage 转发草稿材料探活（创建连接表单） |

---

## 5. 供工作空间使用的元数据

### 5.1 场景

| 场景 | 需要的数据 | 权限视角 |
| --- | --- | --- |
| 工作台左侧树 | 库 / 模式 / 表·视图 | **成员授权** 过滤 |
| 空间「资产授权」指定表 | 某连接下表分页多选 | 操作者对连接有 **asset 可见（data-scope）**；对象按库实际列出（含各 schema），**不强制只 public** |
| 空间「成员授权」指定表 | 表 ⊆ 空间资产已授对象 | 先读 manage 资产授权，再 meta 交集或只展示已授表 |

### 5.2 元数据调用链（已定：方案 A）

| 场景 | 调用链 | 过滤 |
| --- | --- | --- |
| SQL 工作台左侧树 / 工作台元数据 | `前端 → sqlwork /meta/**` | sqlwork 调 manage，按**成员授权**过滤 |
| 资产授权 / 成员授权「自定义对象」 | `前端 → manage GET /workspaces/{id}/meta/**` → 转发用户 JWT → `sqlwork /inner/meta/**` | manage 校验**空间维护权**，且连接为本空间资产 **或** 落在 **data-scope**；sqlwork 只查库、**不做成员表过滤** |

**manage 门面**（经网关 `/dbc-manage`）：

| 方法 | 路径 |
| --- | --- |
| GET | `/workspaces/{workspaceId}/meta/databases?connectionId=` |
| GET | `/workspaces/{workspaceId}/meta/schemas?connectionId=&database=` |
| GET | `/workspaces/{workspaceId}/meta/tables?connectionId=&database=&schema=&keyword=&page=&size=` |

内网 **sqlwork inner 元数据**（manage 转发终端用户 JWT，非 mTLS；供授权配置选表）：

| 方法 | 路径 |
| --- | --- |
| GET | `/inner/meta/databases` |
| GET | `/inner/meta/schemas` |
| GET | `/inner/meta/tables` |

---

## 6. 执行管道（pipeline）

```
1. 校验 JWT、workspaceId、connectionId、sql、sessionId → 初始化 SqlExecuteContext
2. Druid 按方言 parseStatements；条数 ≤ 可配上限（默认 50）
3. 对每条语句依次（结果写入 Context.statements，遇错停）：
   a. 解析 statementType + 表引用
   b. manage 空间鉴权（成员/连接/ops/表）
   c. manage 全局策略：
        BLOCK → 记 ERROR，遇错停
        REAUTH → 无有效 ticket 则返回需二次鉴权；失败遇错停
        ALERT → 记 WARN，继续执行
   d. 执行（见 §6.1 事务）
4. 【末 Stage】AuditStage：按 Context 中每条已执行/已拒绝语句各上报 1 条 sql_op（→ dbc-audit-client → ES）
   —— 鉴权/执行循环内不调用审计；审计失败不阻断已生成的 ExecuteResult
```

**SQL 审计粒度**：一条 SQL = 一条审计记录（同批共享 `batchId`）。详见 [07-audit详细设计](./07-audit详细设计.md) §3.2 / §4.4。

### 6.1 会话与事务（已实现）

| 模式 | 行为 |
| --- | --- |
| **自动提交（默认）** | 每句从池借还；句级提交 |
| **手动提交** | UI 切换；**不隐式 BEGIN**。提示：「请先执行 BEGIN 开启事务；未开启前语句仍自动提交。」用户执行 `BEGIN` 后从池**租约独占连接**；其后同会话语句走该连接直至 `COMMIT`/`ROLLBACK`/关 Tab/超时 |
| **租约时机** | 仅事务开启后独占（省连接）；超时 rollback + 释放 |
| **闲置清理** | 无活动会话默认 30min；事务中闲置默认 15min（可配）。超时清理并 rollback |
| **限额（可配）** | 每用户会话 ≤10；单批语句 ≤50；结果集默认 1000 行 |

API：`POST/PUT/DELETE /sessions`、`POST /sessions/{id}/heartbeat`；`POST /execute` 带 `sessionId`，响应含 `manualMode` / `inTransaction`。  
`BEGIN`/`COMMIT`/`ROLLBACK` 可由 SQL 文本或工具栏按钮提交。

### 6.2 与旧约定

- **废止**「禁止多语句」。  
- **废止** Risk/高危步骤。  

---

## 7. 关于 `public`（已定：测试约定，非产品拦截）

- **联调/自测**：请只对 `public`（及你们自己建的测试表）做写/DDL，避免误改其它 schema。
- **产品行为**：对象浏览、资产选表按**授权与真实元数据**展示各 schema；执行是否允许以 **manage 成员/资产授权 + SQL 操作权限** 为准，**不**额外做「非 public 拒绝写」的硬编码。
- 系统目录（`pg_catalog` / `information_schema`）仍建议默认只读、禁止 DDL（通用安全，与 public 约定无关）。

---

## 8. runtime：池与执行

- 键：`connectionId`（+ 可选 jdbcUrl 指纹）；配置变更时 manage 通知或 sqlwork 短 TTL 失效重建。
- 凭证：每次建池经 manage inner 取解密后的 JDBC URL/user/password（内存短暂使用）；**禁止** sqlwork 库存密文副本。
- Druid：`maxActive` 小（如 5）；`validationQuery` 方言化；空闲驱逐；目标池不开启监控 Servlet。
- 执行：`Statement`/`PreparedStatement`；`setQueryTimeout`；`maxRows`；大字段截断策略（字符串最大长度可配）。
- 取消：本期靠超时；后续再接 `Statement.cancel`。

驱动：与实例上传 JAR 对齐——**首期可用服务 classpath 内官方驱动（PG/MySQL）**；动态加载 manage 落盘 JAR 为增强项（标注 TODO）。

连接池与 Druid SQL Parser 在架构层的选型说明见 [架构设计](../架构/01-架构设计.md)。

---

## 9. 安全与配置

- JWT：与 usercenter / manage 同一 `jwt-secret.txt`。
- mTLS：`dbc-sqlwork` 调 manage / usercenter（代签）。
- 启动注册权限码示例：`sqlwork.execute`、`sqlwork.meta.view`（绑角色另定，经 usercenter inner）。
- 配置项示例：

```yaml
server:
  port: 8007
dbc:
  manage:
    mtls-base-url: https://127.0.0.1:8006   # 或经 Gateway inner 路由
  execute:
    max-rows: 1000
    timeout-seconds: 60
```

服务间签名见 [服务间请求签名](./04-服务间请求签名.md)。本地端口见 [本地启动说明](../../运维/01-本地启动说明.md)。

---

## 10. 与前端 UI 映射

| UI | API |
| --- | --- |
| 选工作空间 / 连接下拉 | sqlwork 调 **manage inner** 后返回前端（或前端直调 manage 公开 API；列表主数据在 manage） |
| 左侧树 | `GET /meta/**` 或 `/meta/tree` |
| 执行 / 结果 | `POST /execute`（maxRows 默认 1000） |
| 资产授权·指定表 | **方案 A**：manage 代理 → sqlwork `/inner/meta/**` |

路由建议：

```
/sqlwork                 选择工作空间
/sqlwork/workspace       工作台编辑页（query/state 带 workspaceId）
```

顶栏「SQL 工作台」位于首页之后；无侧栏。完整 UI 见 [前端与界面设计](./06-前端与界面设计.md)。

---

## 11. 确认结论（全部已定）

| # | 结论 |
| --- | --- |
| 1 | 先 **PostgreSQL**；**`DbDialect` SPI**，业务无库类型 if 堆砌 |
| 2 | **所有权限都校验**（经 manage） |
| 3 | 元数据 **方案 A**：工作台→sqlwork；资产选表→manage→sqlwork inner |
| 4 | **public 仅为测试约定**；对象浏览等按授权正常展示，**不做仅 public 硬拦** |
| 5 | **允许**多语句（Druid 拆分，遇错停） |
| 6 | 默认 **1000** 行/结果集 |
| 7 | 审计 **先结构化日志** + 前端执行日志 |
| 8 | 空间/可用连接：sqlwork 调 **manage inner** |
| 9 | 会话窗口 + 手动事务（`BEGIN` 租约） |
| 10 | 全局策略在 manage；sqlwork 无 Risk |

---

## 12. 实现顺序

1. 建 `dbc-sqlwork` + Nacos/Gateway/JWT + Dialect SPI（PostgresDialect）  
2. manage inner：凭证、鉴权裁决、我的空间/可用连接（缺则先补）  
3. runtime 池 + `POST /execute` + 1000 行 + 单语句  
4. `/meta/**` + `/inner/meta/**`  
5. pipeline 全量鉴权  
6. 前端 `modules/sqlwork`  
7. `MysqlDialect`（结构预留，需要时接入）  
8. audit 上报  

运维提示：本地联调写库请只动 `public`（见 [本地启动说明](../../运维/01-本地启动说明.md)）。

---

## 13. 文档关系

| 文档 | 关系 |
| --- | --- |
| [需求设计](../需求/01-需求设计.md) | 工作空间业务规则、授权模型 |
| [架构设计](../架构/01-架构设计.md) | 模块划分、Druid 连接池/SQL 解析选型、端口与协作 |
| [manage 详设](./02-manage详细设计.md) | 连接/实例资产、inner 鉴权与凭证 |
| [服务间请求签名](./04-服务间请求签名.md) | mTLS 代签 |
| [前端与界面设计](./06-前端与界面设计.md) | SQL 工作台 UI、对象树层次 |

---

## 14. 待增强

| # | 缺口 | 建议 |
| --- | --- | --- |
| 1 | **取消执行**增强 | `Statement.cancel` 与会话模型对齐 |
| 2 | 大结果导出、流式、异步任务 | P2 专文 |
| 3 | 审计切到 **audit 服务** | 对齐 ingest 契约 |
| 4 | 动态 JAR 加载安全模型 | 生产前定案 |
| 5 | 连接池全局总闸、单用户并发上限 | 与会话租约一并运维 |
| 6 | MySQL 方言差异验收清单 | 接入前补测试矩阵 |
| 7 | 前端多会话 / 日志 / 结果 Tab 完整交互 | 契约测试 |
| 8 | 独立风控模块 | 后置 |

冲突时以本文 **§11 已定结论** + 代码为准，并回写本详设。
