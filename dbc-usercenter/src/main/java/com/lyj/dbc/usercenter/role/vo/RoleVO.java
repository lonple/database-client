package com.lyj.dbc.usercenter.role.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * 角色视图对象，面向接口展示。
 */
@Data
@Builder
public class RoleVO {

    /** 角色ID */
    private Long id;

    /** 角色编码 */
    private String code;

    /** 角色名称 */
    private String name;

    /** 角色说明 */
    private String description;

    /**
     * 数据范围。
     * ALL / DEPT_AND_CHILDREN / DEPT_ONLY / CUSTOM
     */
    private String dataScope;

    /** CUSTOM 勾选的部门ID */
    private List<Long> deptIds;

    /**
     * 是否内置。
     * true：是；false：否
     */
    private Boolean builtin;
}
