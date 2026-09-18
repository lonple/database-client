package com.lyj.dbc.client.usercenter.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 权限注册项（与 usercenter PermissionRegisterItem 对齐）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PermissionRegisterItem {

    private String code;
    private String name;
    private String description;
    private String moduleCode;
    private String moduleName;
    private String featureCode;
    private String featureName;
    private Integer sortNo;
}
