package com.lyj.dbc.sqlwork.security;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * 登录用户上下文（写入 SecurityContext / JWT）。
 */
@Data
@AllArgsConstructor
public class LoginUser {

    /** 用户ID */
    private Long userId;

    /** 登录账号 */
    private String username;

    /** 角色编码列表 */
    private List<String> roleCodes;

    /** 权限码列表（JWT 可不含，默认为空） */
    private List<String> permissions;

    public boolean hasSuperAdmin() {
        return roleCodes != null && roleCodes.contains("SUPER_ADMIN");
    }

    public boolean hasSysAdmin() {
        return roleCodes != null && roleCodes.contains("SYS_ADMIN");
    }

    public static LoginUser of(Long userId, String username, String roleCodesCsv) {
        return of(userId, username, roleCodesCsv, null);
    }

    public static LoginUser of(Long userId, String username, String roleCodesCsv, String permissionsCsv) {
        return new LoginUser(userId, username, splitCsv(roleCodesCsv), splitCsv(permissionsCsv));
    }

    private static List<String> splitCsv(String csv) {
        if (csv == null || csv.isBlank()) {
            return Collections.emptyList();
        }
        return Arrays.stream(csv.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }
}
