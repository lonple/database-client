package com.lyj.dbc.manage.authz.user;

import com.lyj.dbc.client.usercenter.dto.UserSummary;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.common.PageResult;
import com.lyj.dbc.manage.security.PermissionCodes;
import com.lyj.dbc.manage.security.SecurityUtils;
import com.lyj.dbc.manage.security.UserContextHolder;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Set;

/**
 * 资产管理侧用户列表：前端调 manage，manage 再调 usercenter inner。
 * <p>
 * 具备工作空间查看/操作权限即可（如 DB_ADMIN）；不要求 usercenter.user.view。
 */
@Validated
@RestController
@RequestMapping("/users")
public class UserFacadeController {

    private final UserFacadeService userFacadeService;

    public UserFacadeController(UserFacadeService userFacadeService) {
        this.userFacadeService = userFacadeService;
    }

    @GetMapping
    public ApiResponse<PageResult<UserSummary>> page(
            @RequestParam(defaultValue = "1") @Min(1) long page,
            @RequestParam(defaultValue = "10") @Min(1) @Max(100) long size,
            @RequestParam(required = false) @Size(max = 64) String username) {
        SecurityUtils.requireUser();
        Set<String> owned = UserContextHolder.permissionCodes();
        boolean ok = PermissionCodes.implies(owned, "auth.workspace.view")
                || PermissionCodes.implies(owned, "auth.workspace.operate");
        if (!ok) {
            throw BizException.forbidden("无权限（需要 auth.workspace.view 或 auth.workspace.operate）");
        }
        com.lyj.dbc.client.common.PageResult<UserSummary> remote = userFacadeService.page(page, size, username);
        List<UserSummary> records = remote.getRecords() == null ? List.of() : remote.getRecords();
        return ApiResponse.ok(new PageResult<>(records, remote.getTotal(), remote.getPage(), remote.getSize()));
    }
}
