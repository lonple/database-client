package com.lyj.dbc.sqlwork.api.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 鉴权裁决请求（转发 manage）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuthzEvaluateRequest {

    private Long userId;
    private Long workspaceId;
    private Long connectionId;
    /** SQL 操作类型，如 SELECT / INSERT */
    private String sqlOp;
    private List<TableRef> tables;
    /** WORKBENCH | EXECUTE */
    private String purpose;
    private String sessionId;
    private String reauthTicket;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableRef {
        private String database;
        private String schema;
        private String name;
    }
}
