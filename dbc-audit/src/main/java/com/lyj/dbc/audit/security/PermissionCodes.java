package com.lyj.dbc.audit.security;

import java.util.Set;

/**
 * 功能权限码蕴含规则（与 usercenter PermissionService.implies 一致）。
 */
public final class PermissionCodes {

    public static final String AUDIT_BIZ_VIEW = "audit.biz.view";
    public static final String AUDIT_SQL_VIEW = "audit.sql.view";

    private PermissionCodes() {
    }

    /**
     * 拥有声明的权限码，或同功能的 operate（当声明为 view 时）即通过。
     */
    public static boolean implies(Set<String> owned, String required) {
        if (owned == null || required == null || required.isBlank()) {
            return false;
        }
        if (owned.contains(required)) {
            return true;
        }
        if (required.endsWith(".view")) {
            String operate = required.substring(0, required.length() - ".view".length()) + ".operate";
            return owned.contains(operate);
        }
        return false;
    }
}
