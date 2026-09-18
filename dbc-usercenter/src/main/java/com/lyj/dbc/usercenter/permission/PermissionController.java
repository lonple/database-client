package com.lyj.dbc.usercenter.permission;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.permission.vo.PermissionModuleVO;
import com.lyj.dbc.usercenter.permission.vo.PermissionVO;
import com.lyj.dbc.usercenter.security.RequirePermission;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 权限管理接口（内置只读）。
 */
@RestController
@RequestMapping("/permissions")
public class PermissionController {

    private final PermissionService permissionService;

    public PermissionController(PermissionService permissionService) {
        this.permissionService = permissionService;
    }

    /**
     * 按模块分组列表（权限管理页）。
     */
    @GetMapping
    @RequirePermission("usercenter.permission.view")
    public ApiResponse<List<PermissionModuleVO>> listGrouped() {
        return ApiResponse.ok(permissionService.listGroupedByModule());
    }

    /**
     * 全部权限扁平列表（功能授权树）。
     */
    @GetMapping("/all")
    @RequirePermission("usercenter.permission.view")
    public ApiResponse<List<PermissionVO>> listAll() {
        return ApiResponse.ok(permissionService.listAll());
    }
}
