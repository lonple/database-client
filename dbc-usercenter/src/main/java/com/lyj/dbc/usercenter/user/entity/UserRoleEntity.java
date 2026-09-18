package com.lyj.dbc.usercenter.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 用户-角色关联，对应表 t_usercenter_user_role。
 */
@Data
@TableName("t_usercenter_user_role")
public class UserRoleEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 用户ID */
    private Long userId;

    /** 角色ID */
    private Long roleId;

    /** 创建时间 */
    private OffsetDateTime createdAt;
}
