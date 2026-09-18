# 详细设计：用户中心（usercenter）

> **服务**：`dbc-usercenter`  
> **包根**：`com.lyj.dbc.usercenter`  
> **对外前缀**：`/dbc-usercenter/**`（经 Gateway `StripPrefix=1`）  
> **关联**：[需求设计](../需求/01-需求设计.md)、[架构设计](../架构/01-架构设计.md)、[服务间请求签名](./04-服务间请求签名.md)、[网关与注册中心](./05-网关与注册中心.md)、[前端与界面设计](./06-前端与界面设计.md)

---

## 1. 定位与边界

| 做 | 不做 |
| --- | --- |
| 登录、JWT、用户 / 部门 / 角色 / 功能权限 | 工作空间、资产 CRUD、SQL 执行 |
| 数据范围解析（`/auth/data-scope`） | 目标库连接与密码 |
| 应用登记、mTLS 客户端证书、ECDSA 代签与公钥 | 空间业务实体（在 manage·authz） |
| 向其它服务提供 inner：权限注册、部门树、用户分页 | 浏览器直连目标库 |

**系统管理**（应用管理）业务在本服务，顶栏独立一级「系统管理」，通常仅超级管理员可见。

平台内置角色：**超级管理员**（`SUPER_ADMIN`）、**系统管理员**（`SYS_ADMIN`）、**数据库管理员**（`DB_ADMIN`）、**数据操作人员**（`DATA_OPERATOR`，仅 SQL 工作台 + 个人空间入口）。  
空间内另有「数据操作人员」空间角色（`OPERATOR`），**不是**同一实体。

---

## 2. 工程与包结构

```
dbc-usercenter/
  src/main/java/com/lyj/dbc/usercenter/
    UserCenterApplication.java
    auth/              # 登录、me、logout、data-scope
    user/              # 用户 CRUD、inner 用户分页
    role/              # 角色 CRUD、功能授权
    dept/              # 部门树 CRUD、inner 部门树
    permission/        # 权限查询、inner 注册与绑角色
    app/               # 应用管理（超管 HTTP）
    mtls/              # mTLS 端口、客户端证书校验
    svcsign/           # 代签客户端、验签、nonce、inner ping
    secrets/           # KEK、SecretFileStore
    security/          # JWT、PermissionAspect、SecurityConfig
    common/            # ApiResponse、BizException、GlobalExceptionHandler
    config/
  src/main/resources/
    application.yml
    db/migration/V1__init.sql   # 开发期全量初始化；稳定后再拆版本
```

| 子域 | 职责 |
| --- | --- |
| **auth** | 账号密码登录、当前用户、数据范围 |
| **user / role / dept / permission** | IAM CRUD 与角色功能授权 |
| **app** | 应用登记、证书重签、签名密钥管理（HTTP 超管面） |
| **mtls** | Tomcat 8044 端口、强制客户端证书、`/inner/apps/keys/**` |
| **svcsign** | 出站代签、入站 `/inner/**` ECDSA 验签 + Redis nonce |
| **security** | JWT HS256 签发与校验、功能权限切面 |

端口：HTTP **8004**；mTLS **8044**（仅密钥 / 代签 API）。注册名、目录名、`spring.application.name` 均为 `dbc-usercenter`。

---

## 3. 数据模型

**Schema**：`usercenter`（**非** `public`）。表前缀 `t_usercenter_*`。Flyway `schemas` / `default-schema` / JDBC `currentSchema=usercenter`。

> **重要**：用户与角色为**多对多**（`t_usercenter_user_role`）；表结构以 `V1__init.sql` 为准，无 `t_usercenter_user.role_id`。

### 3.1 角色 `t_usercenter_role`

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGSERIAL PK | 主键 |
| code | VARCHAR(64) UNIQUE | 如 `SUPER_ADMIN` |
| name | VARCHAR(64) | 名称 |
| description | VARCHAR(255) | 说明 |
| data_scope | VARCHAR(32) | `ALL` / `DEPT_AND_CHILDREN` / `DEPT_ONLY` / `CUSTOM` |
| builtin | SMALLINT | 1 内置 / 0 否 |
| deleted | SMALLINT | 逻辑删除 0/1 |
| created_at / updated_at | TIMESTAMPTZ | |

种子内置角色：`SUPER_ADMIN` / `SYS_ADMIN` / `DB_ADMIN` / `DATA_OPERATOR`。  
权限种子含 `usercenter.personal.space.view`，**绑定全部平台角色**。  
`DATA_OPERATOR` 默认仅绑：`sqlwork.execute`、`sqlwork.meta.view`、`usercenter.personal.space.view`。

### 3.2 用户 `t_usercenter_user`

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGSERIAL PK | 主键 |
| username | VARCHAR(64) UNIQUE | 账号 |
| password_hash | VARCHAR(255) | BCrypt，**永不对外返回** |
| dept_id | BIGINT FK | 归属部门，**可空** |
| mobile | VARCHAR(20) | 可空 |
| description | VARCHAR(512) | 可空 |
| status | SMALLINT | 1 启用 / 0 禁用 |
| builtin | SMALLINT | 内置账号 |
| deleted | SMALLINT | 逻辑删除 |
| created_at / updated_at | TIMESTAMPTZ | |
| created_by / updated_by | BIGINT | 可空 |

种子：`admin` / `admin`（启动时 BCrypt 写入），超级管理员，builtin=1。

### 3.3 用户角色 `t_usercenter_user_role`

| 列 | 说明 |
| --- | --- |
| user_id, role_id | 多对多；创建/编辑用户时 **至少 1 个角色** |
| created_at | |

### 3.4 部门 `t_usercenter_dept`

| 列 | 说明 |
| --- | --- |
| name, description | 同级未删除名称唯一 |
| parent_id | 唯一根预制「默认组织」 |
| path | 物化路径，如 `/1/3/` |
| level | 根为 1，**最多 10 层** |
| deleted, timestamps, created_by / updated_by | |

### 3.5 角色部门 `t_usercenter_role_dept`

| 列 | 说明 |
| --- | --- |
| role_id, dept_id | `data_scope=CUSTOM` 时勾选的部门列表 |

### 3.6 功能权限

**`t_usercenter_permission`**：权限码、模块/功能元数据、sort_no、builtin、逻辑删除。

**`t_usercenter_role_permission`**：角色与权限点多对多。

usercenter 内置权限由 Flyway 种子；其它服务经 inner 幂等注册（见 §9）。

### 3.7 应用与签名密钥（摘要）

**`t_usercenter_app`**：clientId、状态等；历史 `secret_cipher` 列保留但**不再用于鉴权**（改 mTLS 证书）。

**`t_usercenter_app_key`**：`instance_id`、`kid`、ECDSA 公钥、`private_key_cipher`（KEK 加密）等。

实体对外 VO：`UserVO` / `RoleVO`；用户列表含 `roles[]`，兼容字段 `role` 为列表首个。

---

## 4. 部门与数据范围

### 4.1 组织部门

- 表 `t_usercenter_dept`；**唯一根**（预制「默认组织」）；最多 **10** 层；同级未删除部门名称唯一。
- 字段：`name`、`description`、`parent_id`、`path`（如 `/1/3/`）、level`、`deleted`。
- **整部门迁移**：修改父部门后，本节点及整棵子树跟随迁移并重算 `path` / `level`；禁止成环、禁止第二根、子树深度不得超过 10。
- 根部门不可删除；有子部门不可删。

### 4.2 用户与部门 / 角色

- 用户 `dept_id` **可选**（归属部门，可空）。
- 用户与角色 **多对多**（`t_usercenter_user_role`），创建/编辑时 **至少绑定 1 个角色**，可多个。
- 原单字段 `role_id` 已迁移后删除。

### 4.3 数据范围（绑在角色上）

| data_scope | 含义 | 内置默认 |
| --- | --- | --- |
| `ALL` | 全公司 | 超级管理员 |
| `DEPT_AND_CHILDREN` | 归属部门及子部门 | 系统管理员、数据库管理员 |
| `DEPT_ONLY` | 仅归属部门 | 自定义角色可选 |
| `CUSTOM` | 角色勾选部门列表 | 自定义角色可选 |

- **内置角色不可修改、不可删除**（含 data_scope）；管理端可 **新建/编辑/删除非内置角色**。
- `CUSTOM` 使用表 `t_usercenter_role_dept`。
- 多角色可见范围：**并集**；任一角色为 `ALL` → 全公司。
- `DEPT_*` 依赖用户 `dept_id`；无归属部门时这两类贡献空集。
- 资产等后续服务通过用户中心解析后的 scope（如 `/auth/data-scope`）过滤数据。

### 4.4 解析接口

`GET /auth/data-scope` 返回：

```json
{
  "all": false,
  "deptIds": [1, 3, 8],
  "deptId": 3,
  "deptPath": "/1/3/"
}
```

多角色范围取并集；`all=true` 时 `deptIds` 可忽略。

---

## 5. 功能权限

与 [需求设计](../需求/01-需求设计.md) 中数据范围配合：**功能权限**管菜单/接口，**数据范围**管部门数据行。

### 5.1 约定

- 权限码：`{服务短名}.{功能}.{view|operate}`，`operate` 包含 `view`。
- **usercenter** 权限由 Flyway 种子；**其它服务**启动时经 mTLS 调用  
  `POST /inner/permissions/register`、`POST /inner/permissions/bind-roles` 幂等注册并只增绑定角色。
- 权限管理页只读（不维护权限点定义）。
- 超管 / 系统管理员默认拥有用户中心全部权限；跨服务权限由各服务启动时绑定（如 manage → `SUPER_ADMIN` / `SYS_ADMIN` / `DB_ADMIN`）。
- **数据库管理员（`DB_ADMIN`）**：可 **创建公司工作空间** / 变更公司空间所有者（业务在 manage·authz）。
- **数据操作人员（`DATA_OPERATOR`）**：仅 `sqlwork.*` + `usercenter.personal.space.view`；与空间角色 `OPERATOR` 不是同一实体。
- 个人空间入口权限 `usercenter.personal.space.view` 默认绑定**全部**平台角色。
- **角色功能授权**（另需 `usercenter.role.operate`）：
  - **超级管理员**角色：始终只读
  - **系统管理员**角色：超级管理员、系统管理员可改
  - **其他角色**：超管 / 系统管理员 / 其它有 operate 的账号可改
- 授权树 `GET /permissions/all` 校验 `usercenter.permission.view`（与 role 权限分离，不互相 OR）。
- 认证接口不做功能权限校验。
- 模块间权限互不 OR；缺权限由业务流程补齐。
- 无菜单权限：顶栏/侧栏不显示；误入统一回首页。

### 5.2 usercenter 接口权限矩阵

| 资源 | view | operate |
| --- | --- | --- |
| `/users` | GET | POST / PUT / DELETE / password |
| `/depts` | GET | POST / PUT / DELETE |
| `/roles` | GET、GET `/{id}/permissions` | POST / PUT / DELETE、PUT `/{id}/permissions` |
| `/permissions` | GET、GET `/all` | （预留） |
| `/apps` | 超管 | 超管 |

内置权限码种子：

| code | 说明 |
| --- | --- |
| `usercenter.user.view` / `.operate` | 用户管理 |
| `usercenter.dept.view` / `.operate` | 部门管理 |
| `usercenter.role.view` / `.operate` | 角色管理 |
| `usercenter.permission.view` / `.operate` | 权限管理（operate 预留） |

---

## 6. 业务规则

- 登录失败统一文案「用户名或密码错误」；禁用不可登录；未绑定角色不可登录。
- 不可删除 / 禁用内置 `admin`；不可删或禁用当前登录用户。
- 删除为**逻辑删除**（`deleted=1`）。
- 新增用户须指定已有 `roleIds`（至少 1 个）；改密码走独立接口 `PUT /users/{id}/password`；不可改 `username`。
- 部门：根不可删；有子不可删；改父 = 整树迁移，防成环。
- 角色：内置只读；非内置可 CRUD 及配置 `data_scope` / CUSTOM 部门 / 功能权限。
- `DB_ADMIN` 平台角色：具备创建工作空间能力（manage 侧鉴权，见 manage 详设）。

---

## 7. 统一响应与安全

### 7.1 统一响应

```json
{ "code": 0, "message": "ok", "data": {} }
```

分页：`data: { "records", "total", "page", "size" }`。

### 7.2 JWT

- 算法 HS256；密钥 `secrets/jwt-secret.txt` 或环境变量 `DBC_JWT_SECRET`。
- 请求头：`Authorization: Bearer <jwt>`。
- 默认有效期 8 小时（`dbc.jwt.expire-hours`）。
- 401 返回 JSON，不回传栈。

### 7.3 密码

- 用户密码 **BCrypt** 哈希存库。
- 连接凭证等不在本服务（在 manage）。

### 7.4 错误码

| HTTP | 场景 |
| --- | --- |
| 400 | 参数 / 业务规则 |
| 401 | 未登录 / 登录失败 |
| 403 | 无功能权限 |
| 404 | 不存在 |
| 409 | 账号重复 / 同级部门重名 / 角色编码重复 |

---

## 8. 对外 API 契约

对外 Base（经 Gateway）：`/dbc-usercenter`  
下文为**对外完整路径**（Gateway 已 StripPrefix）。  
鉴权：除注明「匿名」外均需 `Authorization: Bearer <jwt>`。

### 8.1 认证

#### POST `/dbc-usercenter/auth/login`（匿名）

请求：

```json
{ "username": "admin", "password": "admin" }
```

响应 `data`：

```json
{
  "token": "<jwt>",
  "expiresIn": 28800,
  "user": {
    "id": 1,
    "username": "admin",
    "mobile": null,
    "description": "内置账号",
    "status": 1,
    "deptId": null,
    "deptName": null,
    "roles": [
      { "id": 1, "code": "SUPER_ADMIN", "name": "超级管理员", "dataScope": "ALL" }
    ],
    "role": { "id": 1, "code": "SUPER_ADMIN", "name": "超级管理员", "dataScope": "ALL" },
    "permissions": ["usercenter.user.operate", "..."]
  }
}
```

> `role` 为兼容字段，等于 `roles[0]`；新客户端应使用 `roles[]`。

#### GET `/dbc-usercenter/auth/me`

需登录；返回当前用户（含 `roles[]`、`permissions[]`）。

#### GET `/dbc-usercenter/auth/data-scope`

需登录；返回 §4.4 结构。

#### POST `/dbc-usercenter/auth/logout`

需登录；前端同时清本地 token（服务端可无状态）。

### 8.2 用户

#### GET `/dbc-usercenter/users`

Query：`page`、`size`、`username`（可选模糊）。

`records` 含：`id, username, mobile, description, status, builtin, deptId, deptName, createdAt, roles[], role`。  
**永不返回** `passwordHash`。

#### POST `/dbc-usercenter/users`

```json
{
  "username": "operator",
  "password": "********",
  "roleIds": [2, 3],
  "deptId": 1,
  "mobile": "13900000000",
  "description": "运维",
  "status": 1
}
```

`roleIds` 至少 1 个；可对应内置或自定义角色。

#### PUT `/dbc-usercenter/users/{id}`

可改：`roleIds, deptId, mobile, description, status`。不可改 `username`。  
`deptId` 传 `null` 表示清空归属部门。

#### DELETE `/dbc-usercenter/users/{id}`

禁止删内置、当前用户。

#### PUT `/dbc-usercenter/users/{id}/password`

```json
{ "password": "new-password" }
```

### 8.3 角色

#### GET `/dbc-usercenter/roles`

返回全部未删除角色（含内置与自定义）；内置三角色：

| code | name | data_scope 默认 |
| --- | --- | --- |
| SUPER_ADMIN | 超级管理员 | ALL |
| SYS_ADMIN | 系统管理员 | DEPT_AND_CHILDREN |
| DB_ADMIN | 数据库管理员 | DEPT_AND_CHILDREN |

#### GET `/dbc-usercenter/roles/{id}`

详情；含 `dataScope`、`deptIds`（CUSTOM 时）。

#### POST `/dbc-usercenter/roles`（非内置）

```json
{
  "code": "OPS_LEAD",
  "name": "运维组长",
  "description": "可选",
  "dataScope": "CUSTOM",
  "deptIds": [2, 5]
}
```

#### PUT `/dbc-usercenter/roles/{id}`

仅非内置；可改 `name, description, dataScope, deptIds`。

#### DELETE `/dbc-usercenter/roles/{id}`

仅非内置；有用户绑定时拒绝。

#### GET `/dbc-usercenter/roles/{id}/permissions`

功能权限 ID 列表回显。

#### PUT `/dbc-usercenter/roles/{id}/permissions`

```json
{ "permissionIds": [1, 2, 5] }
```

受 §5.1 角色授权规则约束。

### 8.4 部门

#### GET `/dbc-usercenter/depts/tree`

整棵部门树。

#### GET `/dbc-usercenter/depts/{id}`

详情。

#### POST `/dbc-usercenter/depts`

```json
{ "parentId": 1, "name": "研发部", "description": "可选" }
```

新增须指定 `parentId`（唯一根已预制）。

#### PUT `/dbc-usercenter/depts/{id}`

可改 `name, description, parentId`（改父 = 整树迁移）。

#### DELETE `/dbc-usercenter/depts/{id}`

根不可删；有子不可删。

### 8.5 权限

#### GET `/dbc-usercenter/permissions`

分页权限点列表（管理页只读）。

#### GET `/dbc-usercenter/permissions/all`

授权树（模块 → 功能 → view/operate）；需 `usercenter.permission.view`。

### 8.6 应用管理（系统管理，超管）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/apps` | 应用列表 |
| POST | `/apps` | 登记应用（立即签发 mTLS 客户端证书） |
| PUT | `/apps/{id}/status` | 启停 |
| POST | `/apps/{id}/reissue-cert` | 重签客户端证书 |
| GET | `/apps/{id}/keys` | 实例签名密钥列表 |
| POST | `/apps/{id}/keys/{kid}/revoke` | 吊销 kid |
| POST | `/apps/self/rotate-signing-key` | 本实例轮换签名密钥 |
| GET | `/apps/self/signing-key` | 本实例当前 kid |

### 8.7 后续服务路径（规划）

```text
/dbc-manage/**
/dbc-sqlwork/**
/dbc-audit/**
```

详见 [架构设计](../架构/01-架构设计.md)。

---

## 9. Inner API

供其它微服务经 **mTLS + ECDSA 验签**（业务 inner）或 **纯 mTLS**（keys API）调用。  
inner 不做终端用户功能权限判定；调用方须自行业务鉴权。

### 9.1 权限注册

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/inner/permissions/register` | 按 code 幂等 upsert 权限点 |
| POST | `/inner/permissions/bind-roles` | 按角色 code 绑定权限码（只增不删未提及绑定） |

请求体见 `PermissionRegisterRequest` / `PermissionBindRolesRequest`。

### 9.2 部门

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/inner/depts/tree` | 整棵部门树（manage 门面等复用） |

### 9.3 用户分页

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/inner/users` | Query：`page, size, username`；供 manage 工作空间选人等 |

manage 对外 `GET /dbc-manage/users` 为门面：校验 `auth.workspace.view|operate`，不要求 `usercenter.user.view`。

### 9.4 密钥 / 代签（mTLS 8044 端口）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/inner/apps/keys/apply` | 申请/复用实例 ECDSA 密钥 |
| POST | `/inner/apps/keys/sign` | 代签业务请求 |
| POST | `/inner/apps/keys/heartbeat` | 心跳 |
| POST | `/inner/apps/keys/rotate` | 轮换 |
| POST | `/inner/apps/keys/revoke` | 吊销 kid |
| GET | `/inner/apps/keys/public` | 拉取存活公钥 |

### 9.5 连通性

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/inner/ping` | 验签连通探测 |

完整签名规范见 [服务间请求签名](./04-服务间请求签名.md)。

---

## 10. 应用管理与 mTLS 摘要

- **一应用一 clientId**；登记时签发客户端证书 → `secrets/mtls/clients/{clientId}.p12`。
- **调中心**：HTTPS + 强制客户端证书（8044）；CN = `clientId`。
- **业务互调**：ECDSA 代签 + 对端本地验签 + Redis nonce 防重放。
- **签名密钥**：一**实例**一对 `kid`；私钥 KEK 加密存 `t_usercenter_app_key`；`secrets/svc-kek.txt`。
- **用户 JWT**：`secrets/jwt-secret.txt`；与各业务服务共享校验。
- HTTP 8004 访问 `/inner/apps/keys/**` **拒绝**；须走 mTLS 端口。

细节、目录结构、待签串格式见 [服务间请求签名](./04-服务间请求签名.md)。

---

## 11. 配置要点

```yaml
server:
  port: 8004

spring:
  application:
    name: dbc-usercenter
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8000
  datasource:
    url: jdbc:postgresql://127.0.0.1:5432/postgres?currentSchema=usercenter
  flyway:
    schemas: usercenter
    default-schema: usercenter

mybatis-plus:
  global-config:
    db-config:
      logic-delete-field: deleted

dbc:
  jwt:
    expire-hours: 8
  secrets:
    dir: ${DBC_SECRETS_DIR:secrets}
  mtls:
    enabled: true
    port: ${DBC_MTLS_PORT:8044}
  svc-sign:
    client-id: dbc-usercenter
    mtls-base-url: ${DBC_MTLS_BASE_URL:https://127.0.0.1:8044}
    timestamp-skew-seconds: 300
    nonce-ttl-seconds: 300
```

端口与本地启动见 [本地启动说明](../../运维/01-本地启动说明.md)。编码与表规范见 [Java 编码规范](../../规范/01-Java编码规范.md)。

---

## 12. 前端映射

| 顶栏 | 侧栏 | 路由 | 权限码前缀 |
| --- | --- | --- | --- |
| 用户中心 | 用户 / 部门 / 角色 / 权限 | `/user-center/*` | `usercenter.*` |
| 系统管理 | 应用管理 | `/system/apps` | 超管 |
| 首页 | — | `/home` | 登录即可 |

- 侧栏顺序：用户管理 → 部门管理 → 角色管理 → **权限管理**（按功能权限过滤）。
- 部门页：左树右详情；支持新增子部门、编辑（含改父 = 迁移）、删除。
- 用户表单：**多选角色**、可选部门树。
- 角色页：可新建自定义角色并配置 `data_scope`；内置只读。
- 菜单过滤：`dbc-front/src/common/permission/menu.ts`；组合式 `usePermission()`。

完整 UI 与路由见 [前端与界面设计](./06-前端与界面设计.md)。

---

## 13. 待增强 / 补充

| # | 缺口 | 建议 |
| --- | --- | --- |
| 1 | **会话失效**（改密、禁用、权限变更）未强制踢下线 | 定黑名单 / 短 TTL / token 版本号方案 |
| 2 | 权限注册「只增不删」长期导致僵尸码 | 补下线 / 废弃流程 |
| 3 | 自定义角色与跨服务权限绑定的运营手册 | 写入运维文档 |
| 4 | 应用证书与密钥**轮换演练**、多实例时钟偏移 | 量化 timestamp 窗口、nonce TTL SLA |
| 5 | `/auth/me` 权限列表体积与缓存 | 大权限集分页或模块懒加载 |
| 6 | 用户中心写操作 **audit** 事件 | 对齐 audit 统一事件模型 |
