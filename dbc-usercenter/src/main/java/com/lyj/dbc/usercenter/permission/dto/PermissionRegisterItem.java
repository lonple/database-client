package com.lyj.dbc.usercenter.permission.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 服务注册权限点条目。
 */
@Data
public class PermissionRegisterItem {

    @NotBlank
    private String code;

    @NotBlank
    private String name;

    private String description;

    @NotBlank
    private String moduleCode;

    @NotBlank
    private String moduleName;

    @NotBlank
    private String featureCode;

    @NotBlank
    private String featureName;

    private Integer sortNo;
}
