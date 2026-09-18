package com.lyj.dbc.manage.authz.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 工作空间成员授权实体。
 */
@Data
@TableName("t_manage_workspace_member_grant")
public class WorkspaceMemberGrantEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long workspaceId;
    private Long userId;
    /** ALL / SPECIFIC */
    private String grantMode;
    private Long connectionId;
    /** ALL_TABLES / SPECIFIC_TABLES */
    private String objectScope;
    private String tablesJson;
    private String opsJson;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
    private Long createdBy;
}
