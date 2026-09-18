package com.lyj.dbc.sqlwork.api.dto;

import lombok.Data;

/**
 * 更新工作台会话（切换连接/库/手动模式）。
 */
@Data
public class UpdateSessionRequest {

    private Long connectionId;
    private String database;
    private String schema;
    private Boolean manualMode;
}
