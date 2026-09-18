package com.lyj.dbc.client.manage.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * manage /inner/sqlwork 相关 DTO（与服务端字段对齐）。
 */
public final class ManageInnerDtos {

    private ManageInnerDtos() {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class WorkspaceSummary {
        private Long id;
        private String name;
        private String description;
        @JsonProperty("role")
        private String myRole;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConnectionSummary {
        @JsonProperty("connectionId")
        private Long connectionId;
        private String name;
        private String dbType;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConnectionMaterial {
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

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AuthzEvaluateRequest {
        private Long userId;
        private Long workspaceId;
        private Long connectionId;
        private String sqlOp;
        @Builder.Default
        private List<TableRef> tables = new ArrayList<>();
        private String purpose;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableRef {
        private String schema;
        private String name;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AuthzEvaluateResult {
        private boolean allowed;
        private String message;
        private boolean connectionAllowed;
        private List<String> grantedOps;
        private List<TableRef> filterTables;
    }
}
