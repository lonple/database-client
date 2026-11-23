-- 登记 askdata 应用（mTLS / 审计客户端身份）
INSERT INTO t_usercenter_app (client_id, app_name, builtin, status, deleted)
SELECT 'dbc-askdata', '智能问数服务', 1, 1, 0
WHERE NOT EXISTS (
    SELECT 1 FROM t_usercenter_app WHERE client_id = 'dbc-askdata' AND deleted = 0
);
