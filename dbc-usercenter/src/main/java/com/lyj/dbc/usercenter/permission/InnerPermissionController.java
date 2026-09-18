package com.lyj.dbc.usercenter.permission;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.mtls.MtlsClientContext;
import com.lyj.dbc.usercenter.permission.dto.PermissionBindRolesRequest;
import com.lyj.dbc.usercenter.permission.dto.PermissionRegisterRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 业务服务启动时经 mTLS 注册权限 / 绑定角色。
 */
@RestController
@RequestMapping("/inner/permissions")
public class InnerPermissionController {

    private final PermissionService permissionService;

    public InnerPermissionController(PermissionService permissionService) {
        this.permissionService = permissionService;
    }

    @PostMapping("/register")
    public ApiResponse<Void> register(@Valid @RequestBody PermissionRegisterRequest request) {
        requireMtlsClientId();
        permissionService.registerPermissions(request.getPermissions());
        return ApiResponse.ok(null);
    }

    @PostMapping("/bind-roles")
    public ApiResponse<Void> bindRoles(@Valid @RequestBody PermissionBindRolesRequest request) {
        requireMtlsClientId();
        permissionService.bindPermissionsToRoles(request.getRoleCodes(), request.getPermissionCodes());
        return ApiResponse.ok(null);
    }

    private String requireMtlsClientId() {
        String clientId = MtlsClientContext.getClientId();
        if (clientId == null || clientId.isBlank()) {
            throw BizException.forbidden("缺少 mTLS 客户端身份");
        }
        return clientId;
    }
}
