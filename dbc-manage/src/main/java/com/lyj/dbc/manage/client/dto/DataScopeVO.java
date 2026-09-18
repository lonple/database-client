package com.lyj.dbc.manage.client.dto;

import lombok.Data;

import java.util.List;

/**
 * 对应用户中心 /auth/data-scope 响应。
 */
@Data
public class DataScopeVO {

    /** 是否全公司（不过滤部门） */
    private Boolean all;

    /** 可见部门ID集合（all=false 时有效） */
    private List<Long> deptIds;

    /** 用户归属部门ID，可空 */
    private Long deptId;

    /** 用户归属部门 path，可空 */
    private String deptPath;
}
