package com.lyj.dbc.usercenter.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 用户实体，对应表 t_usercenter_user。
 */
@Data
@TableName("t_usercenter_user")
public class UserEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 登录账号，唯一，最长64 */
    private String username;

    /** 密码BCrypt哈希，禁止对外返回 */
    private String passwordHash;

    /** 归属部门ID，可空 */
    private Long deptId;

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
     * 1：是；0：否
     */
    private Integer builtin;

    /**
     * 逻辑删除标记。
     * 0：未删除；1：已删除
     */
    @TableLogic
    private Integer deleted;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 更新时间 */
    private OffsetDateTime updatedAt;

    /** 创建人用户ID */
    private Long createdBy;

    /** 更新人用户ID */
    private Long updatedBy;
}
