# 01 Java 编码规范

> 本文件为项目内权威编码规范，供人工扩展与 Agent 读取。  
> Cursor 全局规则同步副本：`%USERPROFILE%\.cursor\rules\java-coding-standards.mdc`。  
> 二者冲突时，以**本仓库文档更新意图**为准，并回写全局规则。  
> 文档路径：`doc/规范/01-Java编码规范.md`。

适用范围：`dbc-*` 后端服务（Java 21 + Spring Boot 3 + MyBatis-Plus 等）。

---

## 1. 业务对象分层（Entity / DTO / BO / VO）

| 类型 | 英文 | 职责 | 典型位置 |
| --- | --- | --- | --- |
| 实体 | **Entity** | 与数据库表映射，字段与表列对应 | `entity` 包或模块下实体类 |
| 传输对象 | **DTO** | 接口层入参/出参；可拆 `*Request` / `*Response` | `dto` |
| 业务对象 | **BO** | 服务层业务组装、跨表/跨领域中间态 | `bo` |
| 视图对象 | **VO** | 面向前端展示的裁剪/聚合结果 | `vo` |

### 使用原则

1. **分层清晰**：Controller 入参用 DTO（Request），出参用 DTO/VO；持久化用 Entity；复杂业务编排用 BO。
2. **禁止直接把 Entity 当接口契约**对外返回（含密码哈希等敏感字段时尤其禁止）。
3. **命名**：
   - Entity：与表语义对应，统一 `XxxEntity`（如 `UserEntity`）。
   - 请求 DTO：`UserCreateRequest`、`LoginRequest`。
   - 响应：`UserVO` / `RoleVO`。
   - BO：`UserAuthBO` 等，体现业务含义。

---

## 2. 字段注释（强制）

对 **Entity、DTO、BO、VO** 中的**每一个属性**，必须添加注释（JavaDoc 优先）。

注释应说明：

- 业务含义
- 取值范围 / 枚举含义（如 `status`：`1` 启用 `0` 禁用）
- 单位、格式（如时间、金额）
- 与库字段的对应关系（Entity）

类上也必须有类注释：职责；Entity 还需注明**对应表名**。

### 示例

```java
/**
 * 用户实体，对应表 t_usercenter_user。
 */
public class UserEntity {

    /** 主键 ID */
    private Long id;

    /** 登录账号，唯一，最长 64 */
    private String username;

    /** 密码哈希（BCrypt），禁止对外返回 */
    private String passwordHash;

    /**
     * 状态。
     * 1：启用；0：禁用
     */
    private Integer status;

    /**
     * 逻辑删除标记。
     * 0：未删除；1：已删除
     */
    private Integer deleted;
}
```

---

## 3. 请求参数校验（强制）

凡作为 **HTTP/RPC 请求体或查询绑定对象** 的属性，必须做参数校验，覆盖：

| 维度 | 常用注解（Jakarta Validation） |
| --- | --- |
| 是否必须 | `@NotNull`、`@NotBlank`、`@NotEmpty` |
| 长度 | `@Size(min=, max=)`、`@Length` |
| 数值范围 | `@Min`、`@Max`、`@DecimalMin`、`@DecimalMax` |
| 格式 | `@Email`、`@Pattern`、`@Mobile`（自定义）等 |

### 约定

1. Controller（或入口 Facade）方法参数加 `@Valid` / `@Validated`。
2. **可选字段**也要限制长度/格式（例如手机号可空，但非空时必须符合格式）。
3. 校验失败信息用中文 `message`，便于前端直接展示。
4. 路径变量、必要 Query 参数同样校验（`@Min(1)` 等）。

### 示例

```java
public class UserCreateRequest {

    /** 登录账号 */
    @NotBlank(message = "账号不能为空")
    @Size(max = 64, message = "账号长度不能超过64")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "账号仅允许字母数字下划线")
    private String username;

    /** 初始密码 */
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 64, message = "密码长度需在6-64之间")
    private String password;

    /** 角色 ID */
    @NotNull(message = "角色不能为空")
    @Min(value = 1, message = "角色ID非法")
    private Long roleId;

    /** 手机号，可选 */
    @Size(max = 20, message = "手机号长度不能超过20")
    @Pattern(regexp = "^$|^1\\d{10}$", message = "手机号格式不正确")
    private String mobile;

    /** 描述，可选 */
    @Size(max = 512, message = "描述长度不能超过512")
    private String description;

    /**
     * 状态。
     * 1：启用；0：禁用
     */
    @NotNull(message = "状态不能为空")
    @Min(0)
    @Max(1)
    private Integer status;
}
```

---

## 4. 数据库建表规范

### 4.1 表名

```text
t_{业务模块}_{实体名}
```

- 全小写，单词间下划线。
- **业务模块**：如 `usercenter`、`datasource`、`sqlwork`。
- **实体名**：如 `user`、`role`、`connection`。
- 若**仅实体名即可无歧义表达业务**，可省略业务模块：`t_{实体名}`。

| 推荐 | 说明 |
| --- | --- |
| `t_usercenter_user` | 用户中心-用户 |
| `t_usercenter_role` | 用户中心-角色 |
| `t_dict` | 全局字典，实体名已足够 |

### 4.2 主键（强制）

- 每张表必须有主键。
- 推荐：`id BIGINT` / `BIGSERIAL`，单列主键。
- 联合主键仅在明确关联表且评审通过后使用。

### 4.3 逻辑删除字段（强制）

- 每张表必须包含逻辑删除字段。
- **统一列名：`deleted`**（对应需求中的 delete 字段；**禁止**使用未加引号的 SQL 保留字 `delete` 作为列名）。
- 类型建议：`SMALLINT NOT NULL DEFAULT 0`（`0` 未删除，`1` 已删除）；或 `BOOLEAN`。
- 业务删除只更新 `deleted`，不物理 DELETE（特殊清理任务除外且需审计）。
- MyBatis-Plus 等 ORM 配置逻辑删除字段为 `deleted`。

### 4.4 注释（强制）

- **表**：必须有表注释。
- **每一个字段**：必须有字段注释。

PostgreSQL 示例：

```sql
CREATE TABLE t_usercenter_user (
    id              BIGSERIAL       PRIMARY KEY,
    username        VARCHAR(64)     NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    status          SMALLINT        NOT NULL DEFAULT 1,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE t_usercenter_user IS '用户中心-用户表';
COMMENT ON COLUMN t_usercenter_user.id IS '主键ID';
COMMENT ON COLUMN t_usercenter_user.username IS '登录账号，唯一';
COMMENT ON COLUMN t_usercenter_user.password_hash IS '密码BCrypt哈希';
COMMENT ON COLUMN t_usercenter_user.status IS '状态：1启用 0禁用';
COMMENT ON COLUMN t_usercenter_user.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_usercenter_user.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_user.updated_at IS '更新时间';
```

### 4.5 与 Entity 对齐

| 库 | Java Entity |
| --- | --- |
| 表注释 / 表名 | 类注释中写明表名 |
| 列注释 | 字段 JavaDoc |
| `deleted` | 字段 + `@TableLogic`（或等价配置） |
| 主键 `id` | `@TableId` |

### 4.6 迁移

- 结构变更必须走 Flyway（或团队选定的迁移工具）。
- 脚本中创建表名、主键、`deleted`、COMMENT** 四要素齐全。
- 历史表改造：新增迁移补齐 `deleted` 与注释，并回填默认值。

---

## 5. 检查清单（提交前）

**对象**

- [ ] 类型选对（Entity/DTO/BO/VO）
- [ ] 类注释完整
- [ ] 每个字段有注释

**请求 DTO**

- [ ] 每字段有必要性/长度/格式等校验
- [ ] 入口使用 `@Valid`

**表结构**

- [ ] 表名符合 `t_[模块_]实体`
- [ ] 有主键
- [ ] 有 `deleted`
- [ ] 表与所有字段有 COMMENT

---

## 6. 后续扩展

可在本文件追加章节（保持编号递增），例如：

- 统一响应体与错误码
- 枚举与字典规范
- 日志与审计字段（`created_by` 等）
- 多租户字段约定

扩展后请同步更新全局规则 `java-coding-standards.mdc` 中的摘要条款。
