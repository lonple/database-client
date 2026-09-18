package com.lyj.dbc.usercenter.role.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 角色-部门勾选（CUSTOM 数据范围），对应表 t_usercenter_role_dept。
 */
@Data
@TableName("t_usercenter_role_dept")
public class RoleDeptEntity {

    /** 主键ID */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 角色ID */
    private Long roleId;

    /** 部门ID */
    private Long deptId;

    /** 创建时间 */
    private OffsetDateTime createdAt;
}
