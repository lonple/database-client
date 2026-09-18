package com.lyj.dbc.usercenter.role;

/**
 * 角色数据范围类型。
 */
public enum DataScopeType {

    /** 全公司，不按部门过滤 */
    ALL,

    /** 用户归属部门及其子部门 */
    DEPT_AND_CHILDREN,

    /** 仅用户归属部门 */
    DEPT_ONLY,

    /** 角色勾选的自定义部门集合 */
    CUSTOM
}
