package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 工作台会话状态。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionVO {

    private String sessionId;
    private Long workspaceId;
    private Long connectionId;
    private String database;
    private String schema;
    private boolean manualMode;
    private boolean inTransaction;
}
