-- usercenter 开发期单一初始化脚本（清库后由 Flyway 执行）
-- 稳定后再拆回按版本号增量迁移

-- ========== 角色 ==========
CREATE TABLE t_usercenter_role (
    id              BIGSERIAL       PRIMARY KEY,
    code            VARCHAR(64)     NOT NULL,
    name            VARCHAR(64)     NOT NULL,
    description     VARCHAR(255),
    builtin         SMALLINT        NOT NULL DEFAULT 1,
    data_scope      VARCHAR(32)     NOT NULL DEFAULT 'DEPT_AND_CHILDREN',
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_usercenter_role_code UNIQUE (code)
);

COMMENT ON TABLE t_usercenter_role IS '用户中心-角色表';
COMMENT ON COLUMN t_usercenter_role.id IS '主键ID';
COMMENT ON COLUMN t_usercenter_role.code IS '角色编码，唯一，如 SUPER_ADMIN';
COMMENT ON COLUMN t_usercenter_role.name IS '角色名称';
COMMENT ON COLUMN t_usercenter_role.description IS '角色说明';
COMMENT ON COLUMN t_usercenter_role.builtin IS '是否内置：1是 0否';
COMMENT ON COLUMN t_usercenter_role.data_scope IS '数据范围：ALL/DEPT_AND_CHILDREN/DEPT_ONLY/CUSTOM';
COMMENT ON COLUMN t_usercenter_role.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_usercenter_role.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_role.updated_at IS '更新时间';

INSERT INTO t_usercenter_role (code, name, description, builtin, data_scope, deleted)
VALUES
    ('SUPER_ADMIN', '超级管理员', '全部权限；admin 归属此角色', 1, 'ALL', 0),
    ('SYS_ADMIN', '系统管理员', '用户与系统配置', 1, 'DEPT_AND_CHILDREN', 0),
    ('DB_ADMIN', '数据库管理员', '创建公司工作空间、变更所有者；数据侧运维与配置', 1, 'DEPT_AND_CHILDREN', 0),
    ('DATA_OPERATOR', '数据操作人员', '仅 SQL 工作台与个人空间入口', 1, 'DEPT_ONLY', 0);

-- ========== 部门 ==========
CREATE TABLE t_usercenter_dept (
    id              BIGSERIAL       PRIMARY KEY,
    name            VARCHAR(64)     NOT NULL,
    description     VARCHAR(512),
    parent_id       BIGINT,
    path            VARCHAR(512)    NOT NULL DEFAULT '/',
    level           SMALLINT        NOT NULL,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      BIGINT,
    updated_by      BIGINT,
    CONSTRAINT fk_t_usercenter_dept_parent FOREIGN KEY (parent_id) REFERENCES t_usercenter_dept (id)
);

COMMENT ON TABLE t_usercenter_dept IS '用户中心-部门表（树形，唯一根）';
COMMENT ON COLUMN t_usercenter_dept.id IS '主键ID';
COMMENT ON COLUMN t_usercenter_dept.name IS '部门名称';
COMMENT ON COLUMN t_usercenter_dept.description IS '部门描述';
COMMENT ON COLUMN t_usercenter_dept.parent_id IS '父部门ID，根节点为空';
COMMENT ON COLUMN t_usercenter_dept.path IS '物化路径，如 /1/3/8/，便于含子部门查询';
COMMENT ON COLUMN t_usercenter_dept.level IS '层级，根为1，最大10';
COMMENT ON COLUMN t_usercenter_dept.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_usercenter_dept.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_dept.updated_at IS '更新时间';
COMMENT ON COLUMN t_usercenter_dept.created_by IS '创建人用户ID';
COMMENT ON COLUMN t_usercenter_dept.updated_by IS '更新人用户ID';

CREATE UNIQUE INDEX uk_t_usercenter_dept_parent_name
    ON t_usercenter_dept (parent_id, name) WHERE deleted = 0 AND parent_id IS NOT NULL;
CREATE UNIQUE INDEX uk_t_usercenter_dept_root_name
    ON t_usercenter_dept (name) WHERE deleted = 0 AND parent_id IS NULL;
CREATE UNIQUE INDEX uk_t_usercenter_dept_single_root
    ON t_usercenter_dept ((1)) WHERE deleted = 0 AND parent_id IS NULL;
CREATE INDEX idx_t_usercenter_dept_parent_id ON t_usercenter_dept (parent_id);
CREATE INDEX idx_t_usercenter_dept_path ON t_usercenter_dept (path);

INSERT INTO t_usercenter_dept (name, description, parent_id, path, level, deleted)
VALUES ('默认组织', '系统预制唯一根部门', NULL, '/', 1, 0);

UPDATE t_usercenter_dept SET path = '/' || id || '/' WHERE parent_id IS NULL;

CREATE TABLE t_usercenter_role_dept (
    id              BIGSERIAL       PRIMARY KEY,
    role_id         BIGINT          NOT NULL,
    dept_id         BIGINT          NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_usercenter_role_dept UNIQUE (role_id, dept_id),
    CONSTRAINT fk_t_usercenter_role_dept_role FOREIGN KEY (role_id) REFERENCES t_usercenter_role (id),
    CONSTRAINT fk_t_usercenter_role_dept_dept FOREIGN KEY (dept_id) REFERENCES t_usercenter_dept (id)
);

COMMENT ON TABLE t_usercenter_role_dept IS '角色自定义数据范围-部门勾选';
COMMENT ON COLUMN t_usercenter_role_dept.role_id IS '角色ID';
COMMENT ON COLUMN t_usercenter_role_dept.dept_id IS '部门ID';
COMMENT ON COLUMN t_usercenter_role_dept.created_at IS '创建时间';

CREATE INDEX idx_t_usercenter_role_dept_role_id ON t_usercenter_role_dept (role_id);

-- ========== 用户（多角色，无单 role_id） ==========
CREATE TABLE t_usercenter_user (
    id              BIGSERIAL       PRIMARY KEY,
    username        VARCHAR(64)     NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    dept_id         BIGINT,
    mobile          VARCHAR(20),
    description     VARCHAR(512),
    status          SMALLINT        NOT NULL DEFAULT 1,
    builtin         SMALLINT        NOT NULL DEFAULT 0,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by      BIGINT,
    updated_by      BIGINT,
    CONSTRAINT uk_t_usercenter_user_username UNIQUE (username),
    CONSTRAINT fk_t_usercenter_user_dept FOREIGN KEY (dept_id) REFERENCES t_usercenter_dept (id)
);

COMMENT ON TABLE t_usercenter_user IS '用户中心-用户表';
COMMENT ON COLUMN t_usercenter_user.id IS '主键ID';
COMMENT ON COLUMN t_usercenter_user.username IS '登录账号，唯一';
COMMENT ON COLUMN t_usercenter_user.password_hash IS '密码BCrypt哈希，禁止对外返回';
COMMENT ON COLUMN t_usercenter_user.dept_id IS '归属部门ID，可空';
COMMENT ON COLUMN t_usercenter_user.mobile IS '手机号';
COMMENT ON COLUMN t_usercenter_user.description IS '用户描述';
COMMENT ON COLUMN t_usercenter_user.status IS '状态：1启用 0禁用';
COMMENT ON COLUMN t_usercenter_user.builtin IS '是否内置账号：1是 0否';
COMMENT ON COLUMN t_usercenter_user.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_usercenter_user.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_user.updated_at IS '更新时间';
COMMENT ON COLUMN t_usercenter_user.created_by IS '创建人用户ID';
COMMENT ON COLUMN t_usercenter_user.updated_by IS '更新人用户ID';

CREATE INDEX idx_t_usercenter_user_created_at ON t_usercenter_user (created_at DESC);
CREATE INDEX idx_t_usercenter_user_dept_id ON t_usercenter_user (dept_id);

CREATE TABLE t_usercenter_user_role (
    id              BIGSERIAL       PRIMARY KEY,
    user_id         BIGINT          NOT NULL,
    role_id         BIGINT          NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_usercenter_user_role UNIQUE (user_id, role_id),
    CONSTRAINT fk_t_usercenter_user_role_user FOREIGN KEY (user_id) REFERENCES t_usercenter_user (id),
    CONSTRAINT fk_t_usercenter_user_role_role FOREIGN KEY (role_id) REFERENCES t_usercenter_role (id)
);

COMMENT ON TABLE t_usercenter_user_role IS '用户-角色多对多';
COMMENT ON COLUMN t_usercenter_user_role.user_id IS '用户ID';
COMMENT ON COLUMN t_usercenter_user_role.role_id IS '角色ID';
COMMENT ON COLUMN t_usercenter_user_role.created_at IS '创建时间';

CREATE INDEX idx_t_usercenter_user_role_user_id ON t_usercenter_user_role (user_id);
CREATE INDEX idx_t_usercenter_user_role_role_id ON t_usercenter_user_role (role_id);

-- ========== 功能权限 ==========
CREATE TABLE t_usercenter_permission (
    id              BIGSERIAL       PRIMARY KEY,
    code            VARCHAR(128)    NOT NULL,
    name            VARCHAR(64)     NOT NULL,
    description     VARCHAR(255),
    module_code     VARCHAR(64)     NOT NULL,
    module_name     VARCHAR(64)     NOT NULL,
    feature_code    VARCHAR(64)     NOT NULL,
    feature_name    VARCHAR(64)     NOT NULL,
    sort_no         INT             NOT NULL DEFAULT 0,
    builtin         SMALLINT        NOT NULL DEFAULT 1,
    deleted         SMALLINT        NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_usercenter_permission_code UNIQUE (code)
);

COMMENT ON TABLE t_usercenter_permission IS '用户中心-功能权限（内置）';
COMMENT ON COLUMN t_usercenter_permission.id IS '主键ID';
COMMENT ON COLUMN t_usercenter_permission.code IS '权限码，如 usercenter.user.operate';
COMMENT ON COLUMN t_usercenter_permission.name IS '权限名称';
COMMENT ON COLUMN t_usercenter_permission.description IS '权限描述';
COMMENT ON COLUMN t_usercenter_permission.module_code IS '业务大模块编码，如 usercenter';
COMMENT ON COLUMN t_usercenter_permission.module_name IS '业务大模块名称';
COMMENT ON COLUMN t_usercenter_permission.feature_code IS '功能模块编码，如 user';
COMMENT ON COLUMN t_usercenter_permission.feature_name IS '功能模块名称';
COMMENT ON COLUMN t_usercenter_permission.sort_no IS '排序号，越小越靠前';
COMMENT ON COLUMN t_usercenter_permission.builtin IS '是否内置：1是 0否';
COMMENT ON COLUMN t_usercenter_permission.deleted IS '逻辑删除：0未删除 1已删除';
COMMENT ON COLUMN t_usercenter_permission.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_permission.updated_at IS '更新时间';

CREATE INDEX idx_t_usercenter_permission_module ON t_usercenter_permission (module_code, feature_code);

CREATE TABLE t_usercenter_role_permission (
    id              BIGSERIAL       PRIMARY KEY,
    role_id         BIGINT          NOT NULL,
    permission_id   BIGINT          NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_t_usercenter_role_permission UNIQUE (role_id, permission_id),
    CONSTRAINT fk_t_usercenter_role_permission_role FOREIGN KEY (role_id) REFERENCES t_usercenter_role (id),
    CONSTRAINT fk_t_usercenter_role_permission_perm FOREIGN KEY (permission_id) REFERENCES t_usercenter_permission (id)
);

COMMENT ON TABLE t_usercenter_role_permission IS '角色-功能权限';
COMMENT ON COLUMN t_usercenter_role_permission.role_id IS '角色ID';
COMMENT ON COLUMN t_usercenter_role_permission.permission_id IS '权限ID';
COMMENT ON COLUMN t_usercenter_role_permission.created_at IS '创建时间';

CREATE INDEX idx_t_usercenter_role_permission_role ON t_usercenter_role_permission (role_id);

INSERT INTO t_usercenter_permission
    (code, name, description, module_code, module_name, feature_code, feature_name, sort_no, builtin, deleted)
VALUES
    ('usercenter.user.view', '用户管理-查看', '查看用户列表与详情', 'usercenter', '用户中心', 'user', '用户管理', 10, 1, 0),
    ('usercenter.user.operate', '用户管理-操作', '新增/编辑/删除/启停/重置密码（含查看）', 'usercenter', '用户中心', 'user', '用户管理', 11, 1, 0),
    ('usercenter.dept.view', '部门管理-查看', '查看部门树与详情', 'usercenter', '用户中心', 'dept', '部门管理', 20, 1, 0),
    ('usercenter.dept.operate', '部门管理-操作', '新增/编辑/删除/迁移部门（含查看）', 'usercenter', '用户中心', 'dept', '部门管理', 21, 1, 0),
    ('usercenter.role.view', '角色管理-查看', '查看角色列表与详情、授权回显', 'usercenter', '用户中心', 'role', '角色管理', 30, 1, 0),
    ('usercenter.role.operate', '角色管理-操作', '新建/编辑/删除自定义角色、功能授权（含查看）', 'usercenter', '用户中心', 'role', '角色管理', 31, 1, 0),
    ('usercenter.permission.view', '权限管理-查看', '查看内置权限列表', 'usercenter', '用户中心', 'permission', '权限管理', 40, 1, 0),
    ('usercenter.permission.operate', '权限管理-操作', '预留；后续可能支持权限维护（含查看）', 'usercenter', '用户中心', 'permission', '权限管理', 41, 1, 0),
    ('usercenter.personal.space.view', '个人空间入口', '用户菜单进入个人空间', 'usercenter', '用户中心', 'personal.space', '个人空间', 50, 1, 0),
    ('manage.instance.view', '实例查看', '查看实例列表与详情', 'manage', '资产管理', 'instance', '实例管理', 110, 0, 0),
    ('manage.instance.operate', '实例操作', '实例增删改、共享与驱动上传', 'manage', '资产管理', 'instance', '实例管理', 120, 0, 0),
    ('manage.connection.view', '连接查看', '查看连接列表与详情（密码掩码）', 'manage', '资产管理', 'connection', '连接管理', 130, 0, 0),
    ('manage.connection.operate', '连接操作', '连接增删改与改密', 'manage', '资产管理', 'connection', '连接管理', 140, 0, 0),
    ('auth.workspace.view', '工作空间授权查看', '查看工作空间列表与详情（权限管控）', 'auth', '权限管控', 'workspace', '工作空间授权', 150, 0, 0),
    ('auth.workspace.operate', '工作空间授权操作', '创建工作空间、成员、资产挂载与成员授权', 'auth', '权限管控', 'workspace', '工作空间授权', 160, 0, 0),
    ('auth.global.policy.view', '全局管控查看', '查看全局管控策略', 'auth', '权限管控', 'global.policy', '全局管控', 170, 0, 0),
    ('auth.global.policy.operate', '全局管控操作', '增删改全局管控策略', 'auth', '权限管控', 'global.policy', '全局管控', 180, 0, 0),
    ('sqlwork.execute', 'SQL 执行', '在工作台执行 SQL', 'sqlwork', 'SQL工作台', 'execute', '执行', 210, 0, 0),
    ('sqlwork.meta.view', '元数据查看', '查看目标库对象树与表列表', 'sqlwork', 'SQL工作台', 'meta', '元数据', 220, 0, 0),
    ('audit.biz.view', '业务审计查看', '查看业务操作审计日志', 'audit', '审计日志', 'biz', '业务日志', 310, 0, 0),
    ('audit.sql.view', 'SQL审计查看', '查看 SQL 操作审计日志', 'audit', '审计日志', 'sql', 'SQL操作日志', 320, 0, 0);

-- 用户中心权限：SUPER_ADMIN / SYS_ADMIN
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.module_code = 'usercenter'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 资产管理（实例/连接）：SUPER_ADMIN / SYS_ADMIN / DB_ADMIN
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN', 'DB_ADMIN')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code IN (
      'manage.instance.view',
      'manage.instance.operate',
      'manage.connection.view',
      'manage.connection.operate'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 权限管控：SUPER_ADMIN / DB_ADMIN
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'DB_ADMIN')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code IN (
      'auth.workspace.view',
      'auth.workspace.operate',
      'auth.global.policy.view',
      'auth.global.policy.operate'
  )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- SQL 工作台：SUPER_ADMIN / SYS_ADMIN / DB_ADMIN / DATA_OPERATOR
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN', 'DB_ADMIN', 'DATA_OPERATOR')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code IN ('sqlwork.execute', 'sqlwork.meta.view')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 审计日志：SUPER_ADMIN / SYS_ADMIN
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code IN ('audit.biz.view', 'audit.sql.view')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 个人空间入口：全部平台角色
-- 注：SUPER_ADMIN/SYS_ADMIN 已在上方 usercenter 模块绑定中包含，此处需幂等补齐 DB_ADMIN/DATA_OPERATOR
INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN', 'DB_ADMIN', 'DATA_OPERATOR')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code = 'usercenter.personal.space.view'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- ========== 应用与密钥 ==========
CREATE TABLE t_usercenter_app (
    id              BIGSERIAL PRIMARY KEY,
    client_id       VARCHAR(64)  NOT NULL,
    app_name        VARCHAR(128) NOT NULL,
    builtin         SMALLINT     NOT NULL DEFAULT 0,
    status          SMALLINT     NOT NULL DEFAULT 1,
    secret_cipher   TEXT,
    deleted         SMALLINT     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uk_usercenter_app_client_id ON t_usercenter_app (client_id) WHERE deleted = 0;

COMMENT ON TABLE t_usercenter_app IS '用户中心-微服务应用登记';
COMMENT ON COLUMN t_usercenter_app.id IS '主键';
COMMENT ON COLUMN t_usercenter_app.client_id IS '应用客户端ID，全局唯一';
COMMENT ON COLUMN t_usercenter_app.app_name IS '应用显示名称';
COMMENT ON COLUMN t_usercenter_app.builtin IS '是否内置：1是 0否';
COMMENT ON COLUMN t_usercenter_app.status IS '状态：1启用 0停用';
COMMENT ON COLUMN t_usercenter_app.secret_cipher IS 'clientSecret 经 KEK 加密后的密文';
COMMENT ON COLUMN t_usercenter_app.deleted IS '逻辑删除：0未删 1已删';
COMMENT ON COLUMN t_usercenter_app.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_app.updated_at IS '更新时间';

CREATE TABLE t_usercenter_app_key (
    id                  BIGSERIAL PRIMARY KEY,
    client_id           VARCHAR(64)  NOT NULL,
    kid                 VARCHAR(128) NOT NULL,
    algorithm           VARCHAR(32)  NOT NULL,
    public_key_pem      TEXT         NOT NULL,
    private_key_cipher  TEXT,
    instance_id         VARCHAR(128),
    status              VARCHAR(16)  NOT NULL DEFAULT 'active',
    deleted             SMALLINT     NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at          TIMESTAMPTZ
);

CREATE UNIQUE INDEX uk_usercenter_app_key_kid ON t_usercenter_app_key (client_id, kid) WHERE deleted = 0;
CREATE INDEX idx_usercenter_app_key_client ON t_usercenter_app_key (client_id) WHERE deleted = 0 AND status = 'active';
CREATE INDEX idx_usercenter_app_key_instance
    ON t_usercenter_app_key (client_id, instance_id)
    WHERE deleted = 0 AND status = 'active';

COMMENT ON TABLE t_usercenter_app_key IS '用户中心-应用签名公钥';
COMMENT ON COLUMN t_usercenter_app_key.id IS '主键';
COMMENT ON COLUMN t_usercenter_app_key.client_id IS '所属应用 clientId';
COMMENT ON COLUMN t_usercenter_app_key.kid IS '密钥ID，验签时按请求头匹配';
COMMENT ON COLUMN t_usercenter_app_key.algorithm IS '算法，如 ES256';
COMMENT ON COLUMN t_usercenter_app_key.public_key_pem IS '公钥 PEM';
COMMENT ON COLUMN t_usercenter_app_key.private_key_cipher IS '私钥经 KEK 加密后的密文（中心代签用）';
COMMENT ON COLUMN t_usercenter_app_key.instance_id IS '注册实例标识，可空';
COMMENT ON COLUMN t_usercenter_app_key.status IS '状态：active / revoked';
COMMENT ON COLUMN t_usercenter_app_key.deleted IS '逻辑删除：0未删 1已删';
COMMENT ON COLUMN t_usercenter_app_key.created_at IS '创建时间';
COMMENT ON COLUMN t_usercenter_app_key.last_seen_at IS '最近心跳时间';
COMMENT ON COLUMN t_usercenter_app_key.revoked_at IS '吊销时间';

INSERT INTO t_usercenter_app (client_id, app_name, builtin, status, deleted)
VALUES
    ('dbc-usercenter', '用户中心', 1, 1, 0),
    ('dbc-manage', '资产管理服务', 1, 1, 0),
    ('dbc-sqlwork', 'SQL工作台服务', 1, 1, 0),
    ('dbc-audit', '审计服务', 1, 1, 0);
