package com.lyj.dbc.usercenter.permission.dto;

import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 按角色 code 只增绑定权限码。
 */
@Data
public class PermissionBindRolesRequest {

    @NotEmpty
    private List<String> roleCodes = new ArrayList<>();

    @NotEmpty
    private List<String> permissionCodes = new ArrayList<>();
}
