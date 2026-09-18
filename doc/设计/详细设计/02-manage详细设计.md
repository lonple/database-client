# 详细设计：资产管理与管控（manage）

> **服务**：`dbc-manage`  
> **包根**：`com.lyj.dbc.manage`  
> **对外前缀**：`/dbc-manage/**`（经 Gateway `StripPrefix=1`）  
> **关联**：[需求设计](../需求/01-需求设计.md)、[架构设计](../架构/01-架构设计.md)、[usercenter 详设](./01-usercenter详细设计.md)、[sqlwork 详设](./03-sqlwork详细设计.md)、[服务间请求签名](./04-服务间请求签名.md)、[前端与界面设计](./06-前端与界面设计.md)

---

## 1. 定位与边界

**管控面**：数据资产、数据权限、安全策略；**不**直连目标库执行用户 SQL。

| 做 | 不做（本期） |
| --- | --- |
| 实例 CRUD、连接 CRUD、驱动 JAR 上传（路径入库） | 连接测试（等 sqlwork `/connections/{id}/ping`） |
| 部门 data-scope 过滤资产 | manage 内加载 JAR 连目标库 |
| 工作空间、成员、资产授权、成员授权、**全局管控策略** | 替代 usercenter 人员主数据 |
| 供 sqlwork 的 inner：空间鉴权、全局策略、凭证、空间/连接摘要 | 列/行级权限；独立高危/风控（后置） |
| 启动注册权限并绑角色 | 权限点前端手工维护 |

连接测试、元数据查库：一律经 **sqlwork**（管理端「指定表」走 manage 代理 sqlwork inner）。

---

## 2. Schema 与工程

### 2.1 平台库 Schema

| 服务 | schema | 说明 |
| --- | --- | --- |
| `dbc-usercenter` | `usercenter` | IAM；Flyway / JDBC `currentSchema=usercenter` |
| `dbc-manage` | `manage` | 本服务；表前缀 `t_manage_*` |
| `dbc-sqlwork` | （可选）`sqlwork` | 执行面；本期可无持久化 schema |
| （规划）`dbc-audit` | `audit` | 审计 |

usercenter 新环境直接建在 `usercenter`；已有库用迁移 `CREATE SCHEMA` + `ALTER TABLE … SET SCHEMA`。

### 2.2 包结构

```
dbc-manage/
  src/main/java/com/lyj/dbc/manage/
    ManageApplication.java
    asset/
      instance/          # 实例 CRUD、驱动上传
      connection/        # 连接 CRUD
      dept/              # 部门门面 DeptFacadeController
      DataScopeSupport.java
    authz/
      WorkspaceAdminController / Service
      user/              # UserFacadeController
      entity/ mapper/ dto/ vo/
    inner/sqlwork/       # 对 sqlwork 的 inner API
    security/            # JWT、PermissionAspect
    bootstrap/           # PermissionRegisterBootstrap
    client/              # UserCenter 出站
    secrets/             # manage-kek
    common/ config/
  src/main/resources/
    application.yml
    db/migration/V1__init.sql   # 开发期全量初始化；稳定后再拆版本
```

| 子域 | 职责 | 优先级 |
| --- | --- | --- |
| **asset** | 实例、连接、驱动 | P0 |
| **authz** | 工作空间、成员、挂载、成员授权；**全局管控策略** | P0 |
| **security** | JWT/权限切面（**无**独立高危业务；风控后置） | P0 |
| **inner/sqlwork** | sqlwork 协作（鉴权 + 全局策略 + ticket） | P0 |

- 端口 **8006**；Gateway `/dbc-manage/**`；Nacos `clientId=dbc-manage`。
- KEK：仓库根 `secrets/manage-kek.txt`（与 usercenter `svc-kek` 分离）；缺失则启动生成。

---

## 3. asset 领域模型

```
实例 Instance                         连接 Connection
─────────────────────                 ─────────────────────
归属部门（独立）                       归属部门（独立，不继承实例）
名称全局唯一                           引用实例
库类型 / host / port                   用户名 + 密码密文（库内）
驱动：原始文件名 + 存储路径等           初始数据库
                                       测试：sqlwork（本期不做前端入口）
```

库类型枚举：`POSTGRESQL` / `MYSQL` / `ORACLE` / `SQLSERVER` / `MARIADB`（可扩展）。

### 3.1 实例（`t_manage_instance`）

| 字段 | 说明 |
| --- | --- |
| id | PK |
| name | **全局唯一** |
| dept_id | 归属部门（必填） |
| db_type | `POSTGRESQL` / `MYSQL` / `ORACLE` / `SQLSERVER` / `MARIADB`（可扩展） |
| host / port | 地址 |
| driver_file_name | 上传时原始文件名（允许重名） |
| driver_storage_path | **实际存储相对路径（唯一）**，如 `drivers/{instanceId}/{uuid}.jar` |
| driver_sha256 / driver_size | 校验与展示 |
| driver_class_name | JDBC 驱动类（可按 db_type 默认，可覆盖） |
| status | 启用/停用（1/0） |
| description | 可选 |
| created_by / updated_by / timestamps / deleted | 惯例 |

**驱动文件：**

- 落盘目录可配置（默认仓库侧 `secrets/manage/drivers/` 或独立 `DBC_MANAGE_DRIVER_DIR`），**不进 Git、不以 BLOB 为主存储**。
- 原始名可重复；**每次上传生成唯一 `driver_storage_path` 再存储**，实例表只记路径与元数据。
- 替换驱动：写新文件并更新路径，旧文件可异步清理。
- 校验：仅 `.jar`、大小上限、路径穿越禁止；仅 `manage.instance.operate` 可上传。

不设独立「驱动管理」菜单与 `t_manage_driver` 表；驱动嵌在实例上。

### 3.2 连接（`t_manage_connection`）

| 字段 | 说明 |
| --- | --- |
| id | PK |
| name | 连接名（**全局唯一**） |
| dept_id | **归属部门（与实例相互独立，必填）** |
| instance_id | 所属实例 |
| db_type | 与实例一致（写入时校验） |
| username | 目标库账号 |
| secret_cipher | **密码经 KEK AES-GCM 加密后存库**；明文不落日志、不回显 |
| initial_database | 初始库 |
| status | 启用/停用 |
| created_by / timestamps / deleted | |

连接测试：创建/编辑表单经 `POST /connections/ping`（manage 组装材料 → sqlwork `/inner/connections/ping` 短超时探活）；已落库亦可 `POST /dbc-sqlwork/connections/{id}/ping`。manage **不**直连目标库。

### 3.3 对外 asset API（摘要）

| 分组 | 路径 | 权限 |
| --- | --- | --- |
| 实例 | `GET/POST /instances`、`GET/PUT/DELETE /instances/{id}` | view / operate |
| 实例 | `GET /instances/selectable` | 建连接时可选实例（data-scope ∩ 启用） |
| 实例 | `POST /instances/{id}/driver` | multipart 驱动上传 |
| 连接 | `GET/POST /connections`、`GET/PUT/DELETE /connections/{id}` | view / operate |

列表/详情按各自 `dept_id` ∩ 当前用户 data-scope 过滤；写入时 `dept_id` 须落在可写范围。

---

## 4. 部门分权方案 A

| 对象 | 部门 | 列表/改删 | 创建连接可选实例 |
| --- | --- | --- | --- |
| 实例 | 运维归属 | 按实例 `dept_id` ∩ data-scope | — |
| 连接 | 账号/密钥归属（与实例独立） | 按连接 `dept_id` ∩ data-scope | 仅能选**数据范围内可见且启用**的实例 |

**不做**实例跨部门共享表。跨部门用实例：调整人员/角色 data-scope，或后续单独做授权能力。

**安全**：能选实例 ≠ 自动看到该实例下其它部门的连接或密码（连接仍按自身 `dept_id` 过滤）。

### 4.1 数据分权实现

- 解析 usercenter data-scope（`all` 或 `deptIds`），经 `DataScopeSupport` / JWT 附带信息。
- 读/写过滤各自资源的 `dept_id`。
- 写入的 `dept_id` 必须落在可写范围；无归属部门用户仅 `ALL` 可建全局资产。

---

## 5. 功能权限码与 bootstrap 注册

### 5.1 权限码

| code | 业务模块（module_code） | 用途 | 默认绑定 |
| --- | --- | --- | --- |
| `manage.instance.view` / `operate` | `manage` 资产管理 | 实例 | SUPER_ADMIN、SYS_ADMIN、DB_ADMIN |
| `manage.connection.view` / `operate` | `manage` 资产管理 | 连接 | 同上 |
| `auth.workspace.view` / `operate` | **`auth` 权限管控** | 工作空间授权 | **SUPER_ADMIN、DB_ADMIN** |
| `auth.global.policy.view` / `operate` | **`auth` 权限管控** | 全局管控 | **SUPER_ADMIN、DB_ADMIN** |

- 权限管理页按 `module_code` 分组：**资产管理**与**权限管控**为两个独立业务模块。
- 一级「权限管控」：任一 `auth.*.view`。
- 一级「资产管理」：任一 `manage.instance.view` / `manage.connection.view`（**不含**工作空间）。

### 5.2 usercenter 扩展（inner）

- `POST /inner/permissions/register`：按 code 幂等 upsert。
- `POST /inner/permissions/bind-roles`：按角色 code 绑定权限码（只增不删未提及绑定）。
- 仅 mTLS；权限管理页仍只读展示。

### 5.3 manage 启动注册

1. 进程**立即启动**，另起后台线程经 mTLS 注册 §5.1 权限码：实例/连接绑三角色；`auth.*` 仅绑 **`SUPER_ADMIN`、`DB_ADMIN`**。
2. 失败则指数退避反复重试（默认 2s 起，封顶 60s），直至成功或进程退出；**不阻断启动**。
3. 注册成功前：前端可能无菜单 / 接口无权限；成功后重新登录或刷新 `/me` 即可。

实现类：`PermissionRegisterBootstrap`。

---

## 6. authz 工作空间

> 完整业务规则与场景见 [需求设计](../需求/01-需求设计.md)（工作空间与权限 / 风险管控章节）。本节为**实现映射**。

### 6.1 分层职责（摘要）

| 层 | 管什么 |
| --- | --- |
| usercenter 功能权限 / 内置角色 | 谁能**创建工作空间**（`DB_ADMIN`）；人员主数据 |
| usercenter data-scope → asset | 可见/维护/挑选授入空间的连接 |
| manage·**authz** | 空间、成员、挂载、成员授权、**全局管控策略** |
| sqlwork | 选空间、SQL 执行、执行前拉空间鉴权 + 全局策略 |

工作空间**与部门无归属关系**；只引用连接，不复制密码。同一连接可挂多空间；运行时**禁止多空间权限并集**。

### 6.1.1 个人空间（已定）

| 项 | 规则 |
| --- | --- |
| 类型 | `t_manage_workspace.space_type`：`COMPANY` \| `PERSONAL` |
| 唯一性 | 每用户至多 1 个 `PERSONAL`（唯一约束 `owner_user_id + space_type` 在 PERSONAL 上） |
| 创建 | 用户自助（个人域）；**不**要求平台 `DB_ADMIN`；本期不做删除/停用 |
| 资产 | 实例/连接增加 `owner_scope`：`COMPANY` \| `PERSONAL` + `owner_user_id`（个人时） |
| 挂载 | **个人连接只能挂本人 PERSONAL 空间**；不可挂 COMPANY 空间、不可挂他人 PERSONAL 空间 |
| 列表隔离 | 个人域 API 只返回本人个人资产/本人个人空间；公司域保持 data-scope |
| 全局管控 | 仅作用于 COMPANY 空间；个人域 UI 不展示全局管控 |

被授权成员：可经 sqlwork「我的空间」进入执行；**不可**改所有者个人资产与授权配置。

### 6.2 实体（表）

| 实体 | 表 | 要点 |
| --- | --- | --- |
| Workspace | `t_manage_workspace` | name；owner_user_id；status；**space_type**（COMPANY/PERSONAL） |
| Member | `t_manage_workspace_member` | user_id + role_code：`OWNER` / `ADMIN` / `OPERATOR` |
| WorkspaceAsset | `t_manage_workspace_asset` | connection_id；object_scope：`CONNECTION`/`DATABASE`/`SCHEMA`/`TABLE`（兼容 ALL_TABLES/SPECIFIC_TABLES）；tables_json 存对象引用；ops_json |
| MemberGrant | `t_manage_workspace_member_grant` | grant_mode：`ALL`/`SPECIFIC`；SPECIFIC 时同上层级 object_scope |

### 6.3 业务规则摘要

完整业务规格见 [需求设计](../需求/01-需求设计.md)。实现要点：

- 详情 Tab：**资产授权** | **成员授权**（成员角色管理收纳在成员授权页）。
- **资产授权**：多连接 + 层级对象 + SQL 操作；连接须在操作者 data-scope 内。
- **成员授权三步**：选用户 → 选对象（**候选 ⊆ 空间资产授权**；宽范围资产内可再选子集）→ 选权限；`POST .../member-grants/batch` 自动加人并写多条 SPECIFIC 授权。
- 后端校验成员 SPECIFIC 授权不得超出空间资产；`grant_mode=ALL` 完全跟随空间资产增减（快捷模式仍保留）。
- 未成员授权：可进空间（若已是成员），工作台不能选任何连接（所有者/空间管理员隐式拥有空间资产除外，见鉴权实现）。
- 运行时禁止多空间权限并集。

对象引用 JSON 示例：`[{"database":"app","schema":"public","name":"t_order"}]`；`DATABASE` 级仅填 database；`SCHEMA` 级填 database+schema；`CONNECTION` 级 tables_json 为空数组。

- **创建公司空间**：仅 `DB_ADMIN`（及 `SUPER_ADMIN` 等等价能力）；创建者 = 所有者（`OWNER`）。
- **创建个人空间**：登录用户自助，每用户一个；创建者 = 所有者。
- **所有者**不可移出；公司空间 `DB_ADMIN` 可更换所有者 → 原所有者降为 `ADMIN`。

### 6.4 执行判定顺序（业务）

```
功能权限 → 已选当前工作空间 → 是成员
  → 连接已挂载 → 成员授权满足
  → 全局管控策略（阻断 / 二次鉴权 / 告警）
  → 允许执行（告警仍执行）
```

### 6.5 对外 API（`/workspaces`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/workspaces` | 创建工作空间（`auth.workspace.operate` + `DB_ADMIN` 等） |
| GET | `/workspaces/mine` | 我加入的空间列表（`auth.workspace.view`） |
| GET | `/workspaces/{id}` | 详情（成员/资产/授权摘要） |
| POST | `/workspaces/{id}/members` | 批量加成员（默认 `OPERATOR`） |
| PUT | `/workspaces/{id}/members/{userId}/role` | 设 `ADMIN` / `OPERATOR`（所有者除外） |
| DELETE | `/workspaces/{id}/members/{userId}` | 移除（所有者不可移除） |
| POST | `/workspaces/{id}/assets` | 资产授权：`connectionId, objectScope, tables?, ops[]` |
| DELETE | `/workspaces/{id}/assets/{assetId}` | 移除空间资产 |
| POST | `/workspaces/{id}/member-grants` | 单条成员授权（兼容） |
| POST | `/workspaces/{id}/member-grants/batch` | 三步向导批量：`userIds` + `targets[]` + `ops`（自动加人） |
| DELETE | `/workspaces/{id}/member-grants/{grantId}` | 移除成员授权 |

### 6.6 全局管控（P0）

表：`t_manage_global_policy`

| 列 | 说明 |
| --- | --- |
| id | 主键 |
| name | 管控名称，唯一 |
| ops_json | SQL 操作数组；UI 提供「所有权限」快捷勾选（展开存全量 DML+DDL ops，不允许空）；DML 与 DDL **可同时多选**（非互斥） |
| strategy | `BLOCK` \| `ALERT` \| `REAUTH` |
| workspace_scope | `ALL` \| `SPECIFIC`；`ALL` 含**之后新建**的空间 |
| workspace_ids_json | SPECIFIC 时的空间 id 列表 |
| sort_no / status / 审计字段 | 排序、启停 |

**对外 API**（权限 `auth.global.policy.*`）：

| 方法 | 路径 |
| --- | --- |
| GET/POST | `/auth/global-policies` |
| GET/PUT/DELETE | `/auth/global-policies/{id}` |

**执行期裁决**（可并入 evaluate 或独立接口）：给定 `workspaceId + sqlOp` → 返回最高优先级命中：`NONE` / `BLOCK` / `REAUTH` / `ALERT` + `policyId` + `policyName`。  
优先级：**BLOCK > REAUTH > ALERT**。

**二次鉴权 ticket**：

| 项 | 约定 |
| --- | --- |
| 签发 | 用户提交当前登录密码 → manage 调 usercenter 校验 → 签发 ticket（随机，服务端缓存） |
| 有效期 | **30s** |
| 范围 | 绑定 `userId + sessionId`（sqlwork 会话窗口）；同窗口共用 |
| 消费 | 执行前携带 ticket；过期或校验失败 → 当前句终止，批遇错停 |
| API | `POST /auth/reauth/ticket`（用户 JWT）；inner 侧 `POST /inner/sqlwork/authz/reauth/verify` |

### 6.7 工作空间授权 Redis 缓存（定案）

**目的**：降低 sqlwork → manage `authz/evaluate` 与连接列表对 PG 的重复读；不缓存最终 allow/deny（组合爆炸）。

#### 规模假设（按业务部门空间）

| 维度 | 假设量级 | 说明 |
| --- | --- | --- |
| 公司空间 | 部门 ≈ 1 个 COMPANY 空间 | 个人空间另算，同一套 key |
| 产品 / 连接 | 每空间 **5～40** 个连接 | 产品≥1 库连接 |
| 表 | 单库 **50～500** 表 | **不按表建 key**；表清单在资产 JSON 内 |
| 运维峰值 | 每产品 ≥1 运维；高峰 **同空间并发 20～50**，全站活跃会话 **200～500** | 热点 = 热空间 assets + 活跃用户 grant |
| Redis 粗算 | 500 空间 × 20 连接 × ~2KB ≈ 数十 MB；活跃用户 key ≈ 数 MB | 远小于按表设 key |

#### Key 设计

前缀：`dbc:authz:`（与 nonce 等其它 key 隔离）

| Key | 类型 | TTL | Value |
| --- | --- | --- | --- |
| `dbc:authz:ws:{wsId}:ver` | STRING | 24h | 空间授权版本（变更时 INCR） |
| `dbc:authz:ws:{wsId}:assets` | HASH | **20min**（命中续期） | field=`c:{connId}` → 资产条目 JSON 数组；首次 miss 整空间加载 |
| `dbc:authz:ws:{wsId}:u:{userId}` | STRING | **10min**（命中续期） | `{role, ver, grants:[…]}`；`ALL` **只存标记**不展开资产 |
| `dbc:authz:ws:{wsId}:uids` | SET | 24h | 曾缓存过的 userId，便于删空间时批量清理 |

用户 JSON 示例：

```json
{
  "role": "OPERATOR",
  "ver": 12,
  "grants": [
    { "mode": "ALL" },
    { "mode": "SPECIFIC", "connectionId": 3, "scope": "TABLE",
      "tables": [{"database":"app","schema":"public","name":"t_order"}],
      "ops": ["SELECT","INSERT"] }
  ]
}
```

PERSONAL / COMPANY **同一套** key。

#### 读写与失效

- **读**：先用户缓存 → OWNER/ADMIN 或 `mode=ALL` 再读 assets HASH；否则用 SPECIFIC。miss 回源 DB 后写入。
- **写**（资产/成员授权/角色/移出）：`INCR ver` + 删除对应 key；**删缓存失败不重试**，依赖 TTL。
- **删空间**：`DEL assets/ver` + 按 `uids` 删用户 key 后删 `uids`；`uids` 缺失时忽略（靠 TTL）。
- **本期不做**：进程内 L1、全局策略缓存、删缓存重试。

#### 热点

对 `assets` / `u:{userId}` 命中后 `EXPIRE` 续期（滑动窗口），热空间与在线运维自然留存更久，冷 key 过期释放。

---

## 7. Inner for sqlwork

Base：`/inner/sqlwork`（应用层 ECDSA 验签 + 调用方身份）。  
sqlwork 出站经 `ManageInnerClient`（mTLS 调 usercenter 代签）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/inner/sqlwork/workspaces/mine` | 当前用户加入的工作空间摘要 |
| GET | `/inner/sqlwork/workspaces/{workspaceId}/connections` | 空间下**已成员授权**的连接摘要 |
| GET | `/inner/sqlwork/workspaces/{workspaceId}/my-authz` | 当前用户在该空间的角色、可访问资产与权限（选空间页） |
| GET | `/inner/sqlwork/connections/{connectionId}/material` | JDBC 建连材料（密码解密后仅响应内存） |
| POST | `/inner/sqlwork/authz/evaluate` | 空间成员/资产鉴权裁决 |
| POST | `/inner/sqlwork/authz/global-policy/evaluate` | 全局策略裁决（可与上合并响应字段） |
| POST | `/inner/sqlwork/authz/reauth/verify` | 校验二次鉴权 ticket |

**鉴权裁决请求** `AuthzEvaluateRequest`：

| 字段 | 说明 |
| --- | --- |
| userId | 当前用户 |
| workspaceId | 工作空间 |
| connectionId | 连接 |
| sqlOp | 如 `SELECT` / `INSERT` |
| tables | `[{ database?, schema, name }]` |
| purpose | `WORKBENCH`：任意 SQL ops 可浏览，返回 `objectFilter`；`EXECUTE`：按 sqlOp/表裁决 |
| sessionId | 可选；二次鉴权关联 |
| reauthTicket | 可选 |

**响应** 扩展：`AuthzEvaluateResult` 含 `grantedOps`、`filterTables`、`objectFilter`（工作台元数据裁剪）及可选全局策略字段（`globalPolicyAction` 等）。

元数据「自定义对象」：前端 → manage `GET /workspaces/{id}/meta/**` → sqlwork `/inner/meta/**`（见 [sqlwork 详设](./03-sqlwork详细设计.md)）。

---

## 8. User facade GET `/users`

**目的**：工作空间成员选择器等场景，**无需** `usercenter.user.view`。

| 方法 | 路径 | 鉴权 |
| --- | --- | --- |
| GET | `/dbc-manage/users` | 需 `auth.workspace.view` **或** `auth.workspace.operate` |

Query：`page`、`size`、`username`（可选模糊）。

实现：`UserFacadeController` → mTLS `GET /inner/users` → 返回 `PageResult<UserSummary>`（id、username 等摘要，不含密码）。

---

## 9. Dept facade GET `/depts/tree`

**目的**：资产表单选部门等，复用 usercenter 部门树且不要求 `usercenter.dept.view`（由 manage 侧业务权限兜底）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/dbc-manage/depts/tree` | manage 校验 asset/workspace 相关 view 后代理 inner |

实现：`DeptFacadeController` → `GET /inner/depts/tree`。

---

## 10. 风控（后置）

本期**不做**独立高危/风控引擎；sqlwork **删除** Risk stub。全局管控与工作空间授权均属**权限校验**。风控另文设计。

---

## 11. 与 sqlwork / usercenter 协作

```
前端 → manage：资产与空间 CRUD、成员/授权配置
前端 → sqlwork：执行与工作台元数据
sqlwork → manage inner：鉴权 + 凭证 + 空间/连接
manage → usercenter inner：data-scope、用户/部门、权限注册
manage → sqlwork inner：代理元数据（资产授权选表）
```

manage **不**加载 JAR、**不**连目标库。日后 sqlwork 经 manage inner 取 `driver_storage_path` 与解密凭证（解密仅在受控内存中）。

---

## 12. 前端映射

| 一级 | 侧栏 | 路由 | 权限 |
| --- | --- | --- | --- |
| **权限管控** | 全局管控、工作空间授权 | `/manage/auth/global-policies`、`/manage/auth/workspaces` | `auth.*` |
| **资产管理** | 实例管理、连接管理 | `/manage/instances`、`/manage/connections` | instance/connection |

| 页面 | 路由 | 要点 |
| --- | --- | --- |
| 全局管控 | `/manage/auth/global-policies` | CRUD；策略三态；空间 ALL/多选 |
| 工作空间列表 | `/manage/auth/workspaces` | 原工作空间页迁移；创建仅 `DB_ADMIN` |
| 工作空间详情 | `/manage/auth/workspaces/:id` | Tab：资产授权 \| 成员授权 |
| 实例 / 连接 | `/manage/instances` 等 | 不变 |

后端 API 前缀仍为 `/dbc-manage/**`（如 `/workspaces`、`/auth/global-policies`），仅前端菜单位置与权限码调整。

完整 UI 见 [前端与界面设计](./06-前端与界面设计.md)。

---

## 13. 已定结论

| 项 | 结论 |
| --- | --- |
| 部门 | 实例与连接 **相互独立**；建连接只能选 data-scope 内可见实例 |
| 菜单 | 「权限管控」+「资产管理」拆分；工作空间在权限管控下 |
| 权限码 | `auth.workspace.*`、`auth.global.policy.*` |
| auth.* 默认角色 | SUPER_ADMIN、DB_ADMIN |
| 全局策略 | BLOCK / ALERT / REAUTH；ALERT 可执行；REAUTH 30s ticket |
| 高危 | **取消**独立业务 |
| 实例名 / 连接名 | **全局唯一** |
| 连接密码 | AES-GCM（`manage-kek`） |
| 工作空间 | 不隶属部门；`DB_ADMIN` 创建；所有者不可移出 |
| 平台角色 | 含 `DATA_OPERATOR`（仅 SQL + 个人空间入口）；空间 `OPERATOR` 为另一实体 |
| 个人空间 | 域切换 + 视觉补强；个人资产仅挂本人 PERSONAL 空间；不做并列「我的*」菜单 |

---

## 14. 待增强

| # | 缺口 | 建议 |
| --- | --- | --- |
| 1 | 资产授权选表：sqlwork 不可达时的错误码/超时/降级 | 定前端提示与重试 |
| 2 | ~~连接/实例变更后 sqlwork 池失效~~ / 授权缓存 | 授权：Redis 缓存已定 §6.7；池失效通知仍待 |
| 3 | 工作空间/资产删除与授权的**级联收回**矩阵 | 补用例级说明 |
| 4 | 驱动文件清理、磁盘配额、多节点共享存储 | 生产定 NAS/对象存储 |
| 5 | manage 操作 **audit** 事件 | 对齐 audit 统一 schema |
| 6 | Oracle/SQLServer 等枚举的默认端口/驱动类映射 | 附方言默认值表 |
| 7 | 更换空间所有者 API | 与 `DB_ADMIN` 规则对齐后暴露 |
| 8 | 独立风控模块 | 后置专文 |

