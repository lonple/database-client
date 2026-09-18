package com.lyj.dbc.manage.security;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

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
            throw com.lyj.dbc.manage.common.BizException.unauthorized("未登录或令牌无效");
        }
        return user;
    }
}
