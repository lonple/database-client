package com.lyj.dbc.audit.security;

import com.lyj.dbc.audit.common.BizException;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * 功能权限校验切面：按当前用户已拥有的权限码判定（含 view←operate 蕴含）。
 */
@Aspect
@Component
public class PermissionAspect {

    @Before("@annotation(requirePermission)")
    public void check(RequirePermission requirePermission) {
        SecurityUtils.requireUser();
        String required = requirePermission.value();
        Set<String> owned = UserContextHolder.permissionCodes();
        if (PermissionCodes.implies(owned, required)) {
            return;
        }
        throw BizException.forbidden("无权限（需要 " + required + "）");
    }
}
