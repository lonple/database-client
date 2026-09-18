package com.lyj.dbc.usercenter.role.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 角色实体，对应表 t_usercenter_role。
 */
@Data
@TableName("t_usercenter_role")
public class RoleEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 角色编码，唯一，如 SUPER_ADMIN */
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
