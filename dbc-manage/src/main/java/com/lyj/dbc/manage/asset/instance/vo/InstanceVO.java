package com.lyj.dbc.manage.asset.instance.vo;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class InstanceVO {

    private Long id;
    private String name;
    private Long deptId;
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
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
