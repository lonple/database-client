package com.lyj.dbc.usercenter.role;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.permission.PermissionService;
import com.lyj.dbc.usercenter.role.dto.RoleCreateRequest;
import com.lyj.dbc.usercenter.role.dto.RolePermissionUpdateRequest;
import com.lyj.dbc.usercenter.role.dto.RoleUpdateRequest;
import com.lyj.dbc.usercenter.role.vo.RoleVO;
import com.lyj.dbc.usercenter.security.RequirePermission;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 角色管理接口。
 */
@Validated
@RestController
@RequestMapping("/roles")
public class RoleController {

    private final RoleService roleService;
    private final PermissionService permissionService;

    public RoleController(RoleService roleService, PermissionService permissionService) {
        this.roleService = roleService;
        this.permissionService = permissionService;
    }

    /**
     * 角色列表。
     */
    @GetMapping
    @RequirePermission("usercenter.role.view")
    public ApiResponse<List<RoleVO>> list() {
        return ApiResponse.ok(roleService.listAll());
    }

    /**
     * 角色详情。
     */
    @GetMapping("/{id}")
    @RequirePermission("usercenter.role.view")
    public ApiResponse<RoleVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(roleService.getById(id));
    }

    /**
     * 新建自定义角色。
     */
    @PostMapping
    @RequirePermission("usercenter.role.operate")
    public ApiResponse<RoleVO> create(@Valid @RequestBody RoleCreateRequest request) {
        return ApiResponse.ok(roleService.create(request));
    }

    /**
     * 更新非内置角色。
     */
    @PutMapping("/{id}")
    @RequirePermission("usercenter.role.operate")
    public ApiResponse<RoleVO> update(@PathVariable @Min(1) Long id,
                                      @Valid @RequestBody RoleUpdateRequest request) {
        return ApiResponse.ok(roleService.update(id, request));
    }

    /**
     * 删除非内置角色。
     */
    @DeleteMapping("/{id}")
    @RequirePermission("usercenter.role.operate")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        roleService.delete(id);
        return ApiResponse.ok(null);
    }

    /**
     * 查询角色已授权权限ID。
     */
    @GetMapping("/{id}/permissions")
    @RequirePermission("usercenter.role.view")
    public ApiResponse<List<Long>> listPermissions(@PathVariable @Min(1) Long id) {
        roleService.getById(id);
        return ApiResponse.ok(permissionService.listPermissionIdsByRole(id));
    }

    /**
     * 保存角色功能授权（仅非内置）。
     */
    @PutMapping("/{id}/permissions")
    @RequirePermission("usercenter.role.operate")
    public ApiResponse<Void> updatePermissions(@PathVariable @Min(1) Long id,
                                               @Valid @RequestBody RolePermissionUpdateRequest request) {
        permissionService.replaceRolePermissions(id, request.getPermissionIds());
        return ApiResponse.ok(null);
    }
}
