package com.lyj.dbc.manage.asset.connection.vo;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class ConnectionVO {

    private Long id;
    private String name;
    private Long deptId;
    private String ownerScope;
    private Long ownerUserId;
    private Long instanceId;
    private String instanceName;
    private String dbType;
    private String username;
    /** 密码掩码，永不回显明文 */
    private String passwordMasked;
    private String initialDatabase;
    private Integer status;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
