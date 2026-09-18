package com.lyj.dbc.audit.ingest;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.audit.common.BizException;
import com.lyj.dbc.audit.es.AuditDocument;
import com.lyj.dbc.audit.es.AuditEsService;
import com.lyj.dbc.client.audit.AuditDetailsNormalizer;
import com.lyj.dbc.client.audit.SensitiveFieldFilter;
import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

/**
 * 审计事件入库：二次敏感字段过滤后写入 ES。
 */
@Service
public class AuditIngestService {

    private static final Logger log = LoggerFactory.getLogger(AuditIngestService.class);

    private final AuditEsService auditEsService;
    private final ObjectMapper objectMapper;

    public AuditIngestService(AuditEsService auditEsService, ObjectMapper objectMapper) {
        this.auditEsService = auditEsService;
        this.objectMapper = objectMapper;
    }

    public int ingest(AuditEventDtos.IngestRequest request) {
        if (request == null || request.getEvents() == null || request.getEvents().isEmpty()) {
            throw BizException.badRequest("events 不能为空");
        }
        int accepted = 0;
        for (AuditEventDtos.AuditEvent event : request.getEvents()) {
            if (event == null) {
                continue;
            }
            AuditDocument doc = toDocument(event);
            auditEsService.index(doc);
            accepted++;
        }
        log.debug("审计 ingest 完成 accepted={}", accepted);
        return accepted;
    }

    @SuppressWarnings("unchecked")
    private AuditDocument toDocument(AuditEventDtos.AuditEvent event) {
        String category = event.getCategory() == null ? "" : event.getCategory().trim().toUpperCase();
        if (!"BIZ".equals(category) && !"SQL".equals(category)) {
            throw BizException.badRequest("category 须为 BIZ 或 SQL");
        }
        String eventId = event.getEventId();
        if (eventId == null || eventId.isBlank()) {
            eventId = UUID.randomUUID().toString();
        }
        Instant occurredAt = event.getOccurredAt() == null ? Instant.now() : event.getOccurredAt();
        String occurredAtIso = occurredAt.truncatedTo(ChronoUnit.MILLIS).toString();

        return AuditDocument.builder()
                .eventId(eventId)
                .category(category)
                .occurredAt(occurredAtIso)
                .operatorUserId(event.getOperatorUserId())
                .operatorUsername(event.getOperatorUsername())
                .clientIp(event.getClientIp())
                .traceId(event.getTraceId())
                .module(event.getModule())
                .action(event.getAction())
                .resourceType(event.getResourceType())
                .resourceId(event.getResourceId())
                .result(event.getResult())
                .failReason(event.getFailReason())
                .details(SensitiveFieldFilter.sanitizeMap(
                        AuditDetailsNormalizer.normalize(event.getDetails(), objectMapper)))
                .batchId(event.getBatchId())
                .statementIndex(event.getStatementIndex())
                .workspaceId(event.getWorkspaceId())
                .workspaceName(event.getWorkspaceName())
                .connectionId(event.getConnectionId())
                .connectionName(event.getConnectionName())
                .dbType(event.getDbType())
                .status(event.getStatus())
                .statementType(event.getStatementType())
                .sqlText(event.getSqlText())
                .sqlTruncated(event.getSqlTruncated())
                .elapsedMs(event.getElapsedMs())
                .failDetail(SensitiveFieldFilter.sanitizeMap(event.getFailDetail()))
                .build();
    }
}
