-- manage 开发期单一初始化脚本（清库后由 Flyway 执行）
-- 稳定后再拆回按版本号增量迁移

-- ========== 资产管理：实例 / 连接 ==========
CREATE TABLE t_manage_instance (
    id                   BIGSERIAL       PRIMARY KEY,
    name                 VARCHAR(128)    NOT NULL,
    dept_id              BIGINT,
    owner_scope          VARCHAR(16)     NOT NULL DEFAULT 'COMPANY',
    owner_user_id        BIGINT,
    db_type              VARCHAR(32)     NOT NULL,
    host                 VARCHAR(255)    NOT NULL,
    port                 INTEGER         NOT NULL,
    driver_file_name     VARCHAR(255),
    driver_storage_path  VARCHAR(512),
    driver_sha256        VARCHAR(64),
    driver_size          BIGINT,
    driver_class_name    VARCHAR(255),
    status               SMALLINT        NOT NULL DEFAULT 1,
    description          VARCHAR(512),
    deleted              SMALLINT        NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by           BIGINT,
    updated_by           BIGINT,
    CONSTRAINT uk_t_manage_instance_name UNIQUE (name),
    CONSTRAINT uk_t_manage_instance_driver_path UNIQUE (driver_storage_path)
);

COMMENT ON TABLE t_manage_instance IS '资产管理-数据库实例';
COMMENT ON COLUMN t_manage_instance.id IS '主键ID';
COMMENT ON COLUMN t_manage_instance.name IS '实例名称，全局唯一';
COMMENT ON COLUMN t_manage_instance.dept_id IS '归属部门ID（公司资产必填；个人资产可空）';
COMMENT ON COLUMN t_manage_instance.owner_scope IS '归属域：COMPANY/PERSONAL';
COMMENT ON COLUMN t_manage_instance.owner_user_id IS '个人资产所有者用户ID';
COMMENT ON COLUMN t_manage_instance.db_type IS '库类型：POSTGRESQL/MYSQL/ORACLE/SQLSERVER/MARIADB';
COMMENT ON COLUMN t_manage_instance.host IS '主机地址';
COMMENT ON COLUMN t_manage_instance.port IS '端口';
COMMENT ON COLUMN t_manage_instance.driver_file_name IS '驱动原始文件名';
COMMENT ON COLUMN t_manage_instance.driver_storage_path IS '驱动存储相对路径，唯一';
COMMENT ON COLUMN t_manage_instance.driver_sha256 IS '驱动文件 SHA-256 十六进制';
COMMENT ON COLUMN t_manage_instance.driver_size IS '驱动文件字节大小';
COMMENT ON COLUMN t_manage_instance.driver_class_name IS 'JDBC 驱动类名';
COMMENT ON COLUMN t_manage_instance.status IS '状态：1启用 0停用';
COMMENT ON COLUMN t_manage_instance.description IS '描述';
COMMENT ON COLUMN t_manage_instance.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_instance.created_at IS '创建时间';
COMMENT ON COLUMN t_manage_instance.updated_at IS '更新时间';
COMMENT ON COLUMN t_manage_instance.created_by IS '创建人用户ID';
COMMENT ON COLUMN t_manage_instance.updated_by IS '更新人用户ID';

CREATE INDEX idx_t_manage_instance_dept_id ON t_manage_instance (dept_id);
CREATE INDEX idx_t_manage_instance_db_type ON t_manage_instance (db_type);
CREATE INDEX idx_t_manage_instance_owner ON t_manage_instance (owner_scope, owner_user_id);

CREATE TABLE t_manage_connection (
    id                 BIGSERIAL       PRIMARY KEY,
    name               VARCHAR(128)    NOT NULL,
    dept_id            BIGINT,
    owner_scope        VARCHAR(16)     NOT NULL DEFAULT 'COMPANY',
    owner_user_id      BIGINT,
    instance_id        BIGINT          NOT NULL,
    db_type            VARCHAR(32)     NOT NULL,
    username           VARCHAR(128)    NOT NULL,
    secret_cipher      TEXT            NOT NULL,
    initial_database   VARCHAR(128),
    status             SMALLINT        NOT NULL DEFAULT 1,
    deleted            SMALLINT        NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by         BIGINT,
    updated_by         BIGINT,
    CONSTRAINT uk_t_manage_connection_name UNIQUE (name),
    CONSTRAINT fk_t_manage_connection_instance
        FOREIGN KEY (instance_id) REFERENCES t_manage_instance (id)
);

COMMENT ON TABLE t_manage_connection IS '资产管理-数据库连接';
COMMENT ON COLUMN t_manage_connection.id IS '主键ID';
COMMENT ON COLUMN t_manage_connection.name IS '连接名称，全局唯一';
COMMENT ON COLUMN t_manage_connection.dept_id IS '归属部门ID（公司资产必填；个人资产可空）';
COMMENT ON COLUMN t_manage_connection.owner_scope IS '归属域：COMPANY/PERSONAL';
COMMENT ON COLUMN t_manage_connection.owner_user_id IS '个人资产所有者用户ID';
COMMENT ON COLUMN t_manage_connection.instance_id IS '所属实例ID';
COMMENT ON COLUMN t_manage_connection.db_type IS '库类型，须与实例一致';
COMMENT ON COLUMN t_manage_connection.username IS '目标库用户名';
COMMENT ON COLUMN t_manage_connection.secret_cipher IS '密码密文（manage-kek AES-GCM）';
COMMENT ON COLUMN t_manage_connection.initial_database IS '初始数据库';
COMMENT ON COLUMN t_manage_connection.status IS '状态：1启用 0停用';
COMMENT ON COLUMN t_manage_connection.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_connection.created_at IS '创建时间';
COMMENT ON COLUMN t_manage_connection.updated_at IS '更新时间';
COMMENT ON COLUMN t_manage_connection.created_by IS '创建人用户ID';
COMMENT ON COLUMN t_manage_connection.updated_by IS '更新人用户ID';

CREATE INDEX idx_t_manage_connection_dept_id ON t_manage_connection (dept_id);
CREATE INDEX idx_t_manage_connection_instance_id ON t_manage_connection (instance_id);
CREATE INDEX idx_t_manage_connection_owner ON t_manage_connection (owner_scope, owner_user_id);

-- ========== 工作空间与授权 ==========
CREATE TABLE t_manage_workspace (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL,
    description     VARCHAR(512),
    owner_user_id   BIGINT          NOT NULL,
    space_type      VARCHAR(16)     NOT NULL DEFAULT 'COMPANY',
    status          SMALLINT        NOT NULL DEFAULT 1,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      BIGINT,
    updated_by      BIGINT,
    CONSTRAINT uk_t_manage_workspace_name UNIQUE (name)
);

COMMENT ON TABLE t_manage_workspace IS '工作空间';
COMMENT ON COLUMN t_manage_workspace.id IS '主键ID';
COMMENT ON COLUMN t_manage_workspace.name IS '空间名称，全局唯一';
COMMENT ON COLUMN t_manage_workspace.description IS '描述';
COMMENT ON COLUMN t_manage_workspace.owner_user_id IS '所有者用户ID';
COMMENT ON COLUMN t_manage_workspace.space_type IS 'COMPANY 公司空间 / PERSONAL 个人空间';
COMMENT ON COLUMN t_manage_workspace.status IS '状态：1启用 0停用';
COMMENT ON COLUMN t_manage_workspace.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_workspace.created_at IS '创建时间';
COMMENT ON COLUMN t_manage_workspace.updated_at IS '更新时间';
COMMENT ON COLUMN t_manage_workspace.created_by IS '创建人用户ID';
COMMENT ON COLUMN t_manage_workspace.updated_by IS '更新人用户ID';

CREATE INDEX idx_t_manage_workspace_owner ON t_manage_workspace (owner_user_id);
CREATE UNIQUE INDEX uk_t_manage_workspace_personal_owner
    ON t_manage_workspace (owner_user_id)
    WHERE space_type = 'PERSONAL' AND deleted = 0;

CREATE TABLE t_manage_workspace_member (
    id              BIGSERIAL       PRIMARY KEY,
    workspace_id    BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL,
    role_code       VARCHAR(32)     NOT NULL,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_manage_workspace_member UNIQUE (workspace_id, user_id),
    CONSTRAINT fk_t_manage_workspace_member_ws
        FOREIGN KEY (workspace_id) REFERENCES t_manage_workspace (id)
);

COMMENT ON TABLE t_manage_workspace_member IS '工作空间成员';
COMMENT ON COLUMN t_manage_workspace_member.id IS '主键ID';
COMMENT ON COLUMN t_manage_workspace_member.workspace_id IS '工作空间ID';
COMMENT ON COLUMN t_manage_workspace_member.user_id IS '成员用户ID';
COMMENT ON COLUMN t_manage_workspace_member.role_code IS '空间角色：OWNER/ADMIN/OPERATOR';
COMMENT ON COLUMN t_manage_workspace_member.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_workspace_member.created_at IS '创建时间';

CREATE INDEX idx_t_manage_workspace_member_user ON t_manage_workspace_member (user_id);

CREATE TABLE t_manage_workspace_asset (
    id              BIGSERIAL       PRIMARY KEY,
    workspace_id    BIGINT          NOT NULL,
    connection_id   BIGINT          NOT NULL,
    object_scope    VARCHAR(32)     NOT NULL,
    tables_json     TEXT,
    ops_json        TEXT            NOT NULL,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      BIGINT,
    CONSTRAINT fk_t_manage_workspace_asset_ws
        FOREIGN KEY (workspace_id) REFERENCES t_manage_workspace (id),
    CONSTRAINT fk_t_manage_workspace_asset_conn
        FOREIGN KEY (connection_id) REFERENCES t_manage_connection (id)
);

COMMENT ON TABLE t_manage_workspace_asset IS '工作空间资产授权（空间上限）';
COMMENT ON COLUMN t_manage_workspace_asset.id IS '主键ID';
COMMENT ON COLUMN t_manage_workspace_asset.workspace_id IS '工作空间ID';
COMMENT ON COLUMN t_manage_workspace_asset.connection_id IS '挂载连接ID';
COMMENT ON COLUMN t_manage_workspace_asset.object_scope IS '对象范围：CONNECTION/DATABASE/SCHEMA/TABLE（兼容 ALL_TABLES/SPECIFIC_TABLES）';
COMMENT ON COLUMN t_manage_workspace_asset.tables_json IS '指定表 JSON 数组；整连接时可为空';
COMMENT ON COLUMN t_manage_workspace_asset.ops_json IS '允许的 SQL 操作 JSON 数组 ["SELECT","INSERT",...]';
COMMENT ON COLUMN t_manage_workspace_asset.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_workspace_asset.created_at IS '创建时间';
COMMENT ON COLUMN t_manage_workspace_asset.created_by IS '创建人用户ID';

CREATE INDEX idx_t_manage_workspace_asset_ws ON t_manage_workspace_asset (workspace_id);
CREATE INDEX idx_t_manage_workspace_asset_conn ON t_manage_workspace_asset (connection_id);

CREATE TABLE t_manage_workspace_member_grant (
    id              BIGSERIAL       PRIMARY KEY,
    workspace_id    BIGINT          NOT NULL,
    user_id         BIGINT          NOT NULL,
    grant_mode      VARCHAR(32)     NOT NULL,
    connection_id   BIGINT,
    object_scope    VARCHAR(32),
    tables_json     TEXT,
    ops_json        TEXT,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      BIGINT,
    CONSTRAINT fk_t_manage_workspace_member_grant_ws
        FOREIGN KEY (workspace_id) REFERENCES t_manage_workspace (id),
    CONSTRAINT fk_t_manage_workspace_member_grant_conn
        FOREIGN KEY (connection_id) REFERENCES t_manage_connection (id)
);

COMMENT ON TABLE t_manage_workspace_member_grant IS '工作空间成员授权';
COMMENT ON COLUMN t_manage_workspace_member_grant.id IS '主键ID';
COMMENT ON COLUMN t_manage_workspace_member_grant.workspace_id IS '工作空间ID';
COMMENT ON COLUMN t_manage_workspace_member_grant.user_id IS '被授权用户ID';
COMMENT ON COLUMN t_manage_workspace_member_grant.grant_mode IS '授权模式：ALL（跟随空间全部资产）/SPECIFIC（指定）';
COMMENT ON COLUMN t_manage_workspace_member_grant.connection_id IS '指定连接ID；grant_mode=ALL 时为空';
COMMENT ON COLUMN t_manage_workspace_member_grant.object_scope IS '对象范围；ALL 模式可空';
COMMENT ON COLUMN t_manage_workspace_member_grant.tables_json IS '指定表 JSON 数组；ALL 模式可空';
COMMENT ON COLUMN t_manage_workspace_member_grant.ops_json IS '允许的 SQL 操作 JSON 数组；ALL 模式可空';
COMMENT ON COLUMN t_manage_workspace_member_grant.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_manage_workspace_member_grant.created_at IS '创建时间';
COMMENT ON COLUMN t_manage_workspace_member_grant.created_by IS '创建人用户ID';

CREATE INDEX idx_t_manage_workspace_member_grant_ws_user
    ON t_manage_workspace_member_grant (workspace_id, user_id);
CREATE INDEX idx_t_manage_workspace_member_grant_conn
    ON t_manage_workspace_member_grant (connection_id);

-- ========== 全局管控 ==========
CREATE TABLE t_manage_global_policy (
    id                  BIGSERIAL       PRIMARY KEY,
    name                VARCHAR(128)    NOT NULL,
    ops_json            TEXT            NOT NULL,
    strategy            VARCHAR(16)     NOT NULL,
    workspace_scope     VARCHAR(16)     NOT NULL DEFAULT 'ALL',
    workspace_ids_json  TEXT,
    sort_no             INT             NOT NULL DEFAULT 0,
    status              SMALLINT        NOT NULL DEFAULT 1,
    deleted             SMALLINT        NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by          BIGINT,
    updated_by          BIGINT,
    CONSTRAINT uk_t_manage_global_policy_name UNIQUE (name)
);

COMMENT ON TABLE t_manage_global_policy IS '全局管控策略';
COMMENT ON COLUMN t_manage_global_policy.name IS '管控名称，全局唯一';
COMMENT ON COLUMN t_manage_global_policy.ops_json IS 'SQL 操作 JSON 数组';
COMMENT ON COLUMN t_manage_global_policy.strategy IS 'BLOCK/ALERT/REAUTH';
COMMENT ON COLUMN t_manage_global_policy.workspace_scope IS 'ALL/SPECIFIC';
COMMENT ON COLUMN t_manage_global_policy.workspace_ids_json IS 'SPECIFIC 时空间 ID JSON 数组';
COMMENT ON COLUMN t_manage_global_policy.sort_no IS '排序，越小越优先（同策略内）';
COMMENT ON COLUMN t_manage_global_policy.status IS '1启用 0停用';
COMMENT ON COLUMN t_manage_global_policy.deleted IS '逻辑删除';

CREATE INDEX idx_t_manage_global_policy_status ON t_manage_global_policy (status, deleted);
