package com.lyj.dbc.manage.security;

import com.lyj.dbc.manage.common.BizException;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * 功能权限校验切面：仅按当前用户已拥有的权限码判定（含 view←operate 蕴含）。
 * 个人域下：持有 {@code usercenter.personal.space.view} 时可访问个人资产/工作空间相关 manage 权限码
 *（不含全局管控），以便 DATA_OPERATOR 等角色自助管理个人空间。
 */
@Aspect
@Component
public class PermissionAspect {

    private static final String PERSONAL_SPACE_VIEW = "usercenter.personal.space.view";

    private static final Set<String> PERSONAL_DOMAIN_MANAGE_PERMS = Set.of(
            "manage.instance.view",
            "manage.instance.operate",
            "manage.connection.view",
            "manage.connection.operate",
            "auth.workspace.view",
            "auth.workspace.operate"
    );

    @Before("@annotation(requirePermission)")
    public void check(RequirePermission requirePermission) {
        SecurityUtils.requireUser();
        String required = requirePermission.value();
        Set<String> owned = UserContextHolder.permissionCodes();
        if (PermissionCodes.implies(owned, required)) {
            return;
        }
        if (DomainContext.isPersonal()
                && PERSONAL_DOMAIN_MANAGE_PERMS.contains(required)
                && PermissionCodes.implies(owned, PERSONAL_SPACE_VIEW)) {
            return;
        }
        throw BizException.forbidden("无权限（需要 " + required + "）");
    }
}
