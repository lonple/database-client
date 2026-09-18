package com.lyj.dbc.usercenter.auth.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * 当前用户解析后的数据权限范围（供资产等服务使用）。
 */
@Data
@Builder
public class DataScopeVO {

    /**
     * 是否全公司。
     * true：不过滤部门
     */
    private Boolean all;

    /** 可见部门ID集合（all=false 时有效） */
    private List<Long> deptIds;

    /** 用户归属部门ID，可空 */
    private Long deptId;

    /** 用户归属部门 path，可空 */
    private String deptPath;
}
