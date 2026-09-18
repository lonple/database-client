package com.lyj.dbc.usercenter.permission.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 功能权限实体，对应表 t_usercenter_permission。
 */
@Data
@TableName("t_usercenter_permission")
public class PermissionEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 权限码，如 usercenter.user.operate */
    private String code;

    /** 权限名称 */
    private String name;

    /** 权限描述 */
    private String description;

    /** 业务大模块编码，如 usercenter */
    private String moduleCode;

    /** 业务大模块名称 */
    private String moduleName;

    /** 功能模块编码，如 user */
    private String featureCode;

    /** 功能模块名称 */
    private String featureName;

    /** 排序号，越小越靠前 */
    private Integer sortNo;

    /**
     * 是否内置。
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
}
