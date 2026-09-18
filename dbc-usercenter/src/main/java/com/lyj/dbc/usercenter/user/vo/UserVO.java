package com.lyj.dbc.usercenter.user.vo;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * 用户视图对象，面向接口展示（不含密码）。
 */
@Data
@Builder
public class UserVO {

    /** 用户ID */
    private Long id;

    /** 登录账号 */
    private String username;

    /** 手机号 */
    private String mobile;

    /** 用户描述 */
    private String description;

    /**
     * 状态。
     * 1：启用；0：禁用
     */
    private Integer status;

    /**
     * 是否内置账号。
     * true：是；false：否
     */
    private Boolean builtin;

    /** 归属部门ID，可空 */
    private Long deptId;

    /** 归属部门名称，可空 */
    private String deptName;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 角色列表 */
    private List<RoleBrief> roles;

    /**
     * 兼容展示：主角色（列表首个）。
     */
    private RoleBrief role;

    /**
     * 功能权限码并集（仅登录 / me 填充；用户列表可为 null）。
     */
    private List<String> permissions;

    /**
     * 用户关联的角色摘要。
     */
    @Data
    @Builder
    public static class RoleBrief {

        /** 角色ID */
        private Long id;

        /** 角色编码 */
        private String code;

        /** 角色名称 */
        private String name;

        /** 数据范围 */
        private String dataScope;
    }
}
