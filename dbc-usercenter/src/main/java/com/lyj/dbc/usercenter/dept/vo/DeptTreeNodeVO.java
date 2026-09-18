package com.lyj.dbc.usercenter.dept.vo;

import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 部门树节点。
 */
@Data
@Builder
public class DeptTreeNodeVO {

    /** 部门ID */
    private Long id;

    /** 部门名称 */
    private String name;

    /** 部门描述 */
    private String description;

    /** 父部门ID */
    private Long parentId;

    /** 层级 */
    private Integer level;

    /** 物化路径 */
    private String path;

    /** 子部门 */
    @Builder.Default
    private List<DeptTreeNodeVO> children = new ArrayList<>();
}
