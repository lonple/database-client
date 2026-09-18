package com.lyj.dbc.manage.asset.instance.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 数据库实例实体。
 */
@Data
@TableName("t_manage_instance")
public class InstanceEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;
    private Long deptId;
    /** COMPANY / PERSONAL */
    private String ownerScope;
    private Long ownerUserId;
    private String dbType;
    private String host;
    private Integer port;
    private String driverFileName;
    private String driverStoragePath;
    private String driverSha256;
    private Long driverSize;
    private String driverClassName;
    private Integer status;
    private String description;

    @TableLogic
    private Integer deleted;

    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Long createdBy;
    private Long updatedBy;
}
