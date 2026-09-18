package com.lyj.dbc.usercenter.dept.vo;

import lombok.Builder;
import lombok.Data;

/**
 * 部门详情。
 */
@Data
@Builder
public class DeptVO {

    /** 部门ID */
    private Long id;

    /** 部门名称 */
    private String name;

    /** 部门描述 */
    private String description;

    /** 父部门ID */
    private Long parentId;

    /** 父部门名称 */
    private String parentName;

    /** 层级 */
    private Integer level;

    /** 物化路径 */
    private String path;

    /** 是否根部门 */
    private Boolean root;
}
