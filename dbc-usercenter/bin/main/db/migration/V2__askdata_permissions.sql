-- 智能问数监控权限
INSERT INTO t_usercenter_permission (
    code, name, description, module_code, module_name, feature_code, feature_name, sort_no, builtin, deleted
) VALUES
    ('audit.askdata.view', '智能问数监控查看', '查看智能问数 LLM 运行监控与 span', 'audit', '审计日志', 'askdata', '智能问数监控', 330, 0, 0)
ON CONFLICT (code) DO NOTHING;

INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code = 'audit.askdata.view'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 问数业务权限（工作台入口）
INSERT INTO t_usercenter_permission (
    code, name, description, module_code, module_name, feature_code, feature_name, sort_no, builtin, deleted
) VALUES
    ('askdata.use', '智能问数使用', '使用智能问数工作台：工程/会话/执行', 'askdata', '智能问数', 'use', '使用', 410, 0, 0)
ON CONFLICT (code) DO NOTHING;

INSERT INTO t_usercenter_role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM t_usercenter_role r
CROSS JOIN t_usercenter_permission p
WHERE r.code IN ('SUPER_ADMIN', 'SYS_ADMIN', 'DB_ADMIN', 'DATA_OPERATOR')
  AND r.deleted = 0
  AND p.deleted = 0
  AND p.code = 'askdata.use'
ON CONFLICT (role_id, permission_id) DO NOTHING;
