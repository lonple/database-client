package com.lyj.dbc.manage.authz.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 工作空间成员实体。
 */
@Data
@TableName("t_manage_workspace_member")
public class WorkspaceMemberEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long workspaceId;
    private Long userId;
    /** OWNER / ADMIN / OPERATOR */
    private String roleCode;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
}
