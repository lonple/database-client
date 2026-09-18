package com.lyj.dbc.manage.inner.sqlwork.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 目标库连接材料（明文仅内存短暂使用；与 sqlwork ConnectionMaterial 字段一致）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionMaterialVO {

    private Long connectionId;
    private String name;
    private String dbType;
    private String jdbcUrl;
    private String username;
    private String password;
    private String driverClassName;
    private String initialDatabase;
    private String host;
    private Integer port;
}
