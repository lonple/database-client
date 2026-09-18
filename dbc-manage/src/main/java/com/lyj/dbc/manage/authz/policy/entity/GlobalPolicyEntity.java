package com.lyj.dbc.manage.authz.policy.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 全局管控策略。
 */
@Data
@TableName("t_manage_global_policy")
public class GlobalPolicyEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;
    private String opsJson;
    /** BLOCK / ALERT / REAUTH */
    private String strategy;
    /** ALL / SPECIFIC */
    private String workspaceScope;
    private String workspaceIdsJson;
    private Integer sortNo;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
}
