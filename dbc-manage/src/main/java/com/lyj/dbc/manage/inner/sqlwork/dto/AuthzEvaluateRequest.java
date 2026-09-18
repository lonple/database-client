package com.lyj.dbc.manage.inner.sqlwork.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 鉴权裁决请求（与 sqlwork 客户端字段一致）。
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
    /** 会话窗口 ID（二次鉴权 ticket 绑定） */
    private String sessionId;
    /** 二次鉴权 ticket */
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
