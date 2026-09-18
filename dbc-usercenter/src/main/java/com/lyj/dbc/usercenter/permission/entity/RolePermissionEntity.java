package com.lyj.dbc.usercenter.permission.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 角色-功能权限，对应表 t_usercenter_role_permission。
 */
@Data
@TableName("t_usercenter_role_permission")
public class RolePermissionEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 角色ID */
    private Long roleId;

    /** 权限ID */
    private Long permissionId;

    /** 创建时间 */
    private OffsetDateTime createdAt;
}
