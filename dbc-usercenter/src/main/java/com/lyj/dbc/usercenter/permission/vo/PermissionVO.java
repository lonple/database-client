package com.lyj.dbc.usercenter.permission.vo;

import lombok.Builder;
import lombok.Data;

/**
 * 权限视图。
 */
@Data
@Builder
public class PermissionVO {

    /** 权限ID */
    private Long id;

    /** 权限码 */
    private String code;

    /** 权限名称 */
    private String name;

    /** 权限描述 */
    private String description;

    /** 业务大模块编码 */
    private String moduleCode;

    /** 业务大模块名称 */
    private String moduleName;

    /** 功能模块编码 */
    private String featureCode;

    /** 功能模块名称 */
    private String featureName;

    /** 排序号 */
    private Integer sortNo;

    /** 是否内置 */
    private Boolean builtin;
}
