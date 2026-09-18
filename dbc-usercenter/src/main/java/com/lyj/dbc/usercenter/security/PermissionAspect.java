package com.lyj.dbc.usercenter.security;

import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.permission.PermissionService;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.stereotype.Component;

import java.util.HashSet;
import java.util.Set;

/**
 * 功能权限校验切面。
 */
@Aspect
@Component
public class PermissionAspect {

    private final PermissionService permissionService;

    public PermissionAspect(PermissionService permissionService) {
        this.permissionService = permissionService;
    }

    @Before("@annotation(requirePermission)")
    public void check(RequirePermission requirePermission) {
        LoginUser user = SecurityUtils.requireUser();
        Set<String> owned = new HashSet<>(permissionService.listPermissionCodesByUser(user.getUserId()));
        if (!PermissionService.implies(owned, requirePermission.value())) {
            throw BizException.forbidden("无权限");
        }
    }
}
