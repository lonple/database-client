package com.lyj.dbc.manage.authz.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 工作空间资产授权实体。
 */
@Data
@TableName("t_manage_workspace_asset")
public class WorkspaceAssetEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long workspaceId;
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
