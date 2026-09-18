package com.lyj.dbc.audit.security;

import com.lyj.dbc.audit.common.BizException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

/**
 * 当前登录用户与 Authorization 头工具。
 */
public final class SecurityUtils {

    private SecurityUtils() {
    }

    public static LoginUser currentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof LoginUser loginUser)) {
            return null;
        }
        return loginUser;
    }

    public static LoginUser requireUser() {
        LoginUser user = currentUser();
        if (user == null) {
            throw BizException.unauthorized("未登录或令牌无效");
        }
        return user;
    }

    /**
     * 取原始 JWT 字符串（不含 Bearer 前缀），用于转发 Authorization。
     */
    public static String requireBearerToken() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getCredentials() instanceof String token)
                || token.isBlank()) {
            throw BizException.unauthorized("未登录或令牌无效");
        }
        return token;
    }

    /** 完整 Authorization 头值：Bearer &lt;token&gt; */
    public static String requireAuthorizationHeader() {
        return "Bearer " + requireBearerToken();
    }
}
