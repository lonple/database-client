package com.lyj.dbc.usercenter.role.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 角色功能授权请求。
 */
@Data
public class RolePermissionUpdateRequest {

    /** 权限ID列表，可空表示清空 */
    @NotNull(message = "权限列表不能为空（可传空数组）")
    private List<Long> permissionIds = new ArrayList<>();
}
