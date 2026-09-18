package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 目标库连接材料（明文仅内存短暂使用）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionMaterial {

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
