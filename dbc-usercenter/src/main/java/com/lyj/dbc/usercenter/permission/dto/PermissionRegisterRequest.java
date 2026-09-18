package com.lyj.dbc.usercenter.permission.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 批量注册权限点。
 */
@Data
public class PermissionRegisterRequest {

    @NotEmpty
    @Valid
    private List<PermissionRegisterItem> permissions = new ArrayList<>();
}
