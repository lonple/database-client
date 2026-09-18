package com.lyj.dbc.manage.asset.connection.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 数据库连接实体。
 */
@Data
@TableName("t_manage_connection")
public class ConnectionEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;
    private Long deptId;
    /** COMPANY / PERSONAL */
    private String ownerScope;
    private Long ownerUserId;
    private Long instanceId;
    private String dbType;
    private String username;
    private String secretCipher;
    private String initialDatabase;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
}
