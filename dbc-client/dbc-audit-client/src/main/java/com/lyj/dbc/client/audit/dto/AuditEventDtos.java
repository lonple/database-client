package com.lyj.dbc.client.audit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 审计 ingest 载荷（与 dbc-audit /inner/events 对齐）。
 */
public final class AuditEventDtos {

    private AuditEventDtos() {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IngestRequest {
        private List<AuditEvent> events;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AuditEvent {
        private String eventId;
        /** BIZ / SQL */
        private String category;
        private Instant occurredAt;
        private Long operatorUserId;
        private String operatorUsername;
        private String clientIp;
        private String traceId;

        // ---- BIZ ----
        private String module;
        private String action;
        private String resourceType;
        private String resourceId;
        private String result;
        private String failReason;
        private Map<String, Object> details;

        // ---- SQL ----
        private String batchId;
        private Integer statementIndex;
        private Long workspaceId;
        private String workspaceName;
        private Long connectionId;
        private String connectionName;
        private String dbType;
        private String status;
        private String statementType;
        private String sqlText;
        private Boolean sqlTruncated;
        private Long elapsedMs;
        private Map<String, Object> failDetail;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IngestResult {
        private int accepted;
    }
}
