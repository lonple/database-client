package com.lyj.dbc.manage.security;

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

    public boolean hasSuperAdmin() {
        return roleCodes != null && roleCodes.contains("SUPER_ADMIN");
    }

    public boolean hasSysAdmin() {
        return roleCodes != null && roleCodes.contains("SYS_ADMIN");
    }

    public static LoginUser of(Long userId, String username, String roleCodesCsv) {
        List<String> codes;
        if (roleCodesCsv == null || roleCodesCsv.isBlank()) {
            codes = Collections.emptyList();
        } else {
            codes = Arrays.stream(roleCodesCsv.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .toList();
        }
        return new LoginUser(userId, username, codes);
    }
}
