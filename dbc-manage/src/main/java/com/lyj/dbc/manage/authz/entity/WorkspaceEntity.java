package com.lyj.dbc.manage.authz.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 工作空间实体。
 */
@Data
@TableName("t_manage_workspace")
public class WorkspaceEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;
    private String description;
    private Long ownerUserId;
    /** COMPANY / PERSONAL */
    private String spaceType;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
}
