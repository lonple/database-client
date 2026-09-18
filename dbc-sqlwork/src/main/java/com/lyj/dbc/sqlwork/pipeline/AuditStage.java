package com.lyj.dbc.sqlwork.pipeline;

import com.lyj.dbc.client.audit.AuditIngestClient;
import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 管道末位：将 Context 中已产生的语句异步上报审计（一句一条）。
 */
@Component
public class AuditStage {

    private static final Logger log = LoggerFactory.getLogger(AuditStage.class);

    private final ObjectProvider<AuditIngestClient> auditIngestClient;

    public AuditStage(ObjectProvider<AuditIngestClient> auditIngestClient) {
        this.auditIngestClient = auditIngestClient;
    }

    public void flush(SqlExecuteContext context) {
        if (context == null || context.getStatements() == null || context.getStatements().isEmpty()) {
            return;
        }
        AuditIngestClient client = auditIngestClient.getIfAvailable();
        if (client == null) {
            log.debug("AuditIngestClient 未装配，跳过 SQL 审计上报");
            return;
        }
        String batchId = context.getBatchId() == null || context.getBatchId().isBlank()
                ? UUID.randomUUID().toString()
                : context.getBatchId();
        List<AuditEventDtos.AuditEvent> events = new ArrayList<>(context.getStatements().size());
        Instant now = Instant.now();
        for (SqlExecuteContext.StatementAuditItem item : context.getStatements()) {
            events.add(AuditEventDtos.AuditEvent.builder()
                    .eventId(UUID.randomUUID().toString())
                    .category("SQL")
                    .occurredAt(now)
                    .operatorUserId(context.getOperatorUserId())
                    .operatorUsername(context.getOperatorUsername())
                    .clientIp(context.getClientIp())
                    .batchId(batchId)
                    .statementIndex(item.getStatementIndex())
                    .workspaceId(context.getWorkspaceId())
                    .workspaceName(context.getWorkspaceName())
                    .connectionId(context.getConnectionId())
                    .connectionName(context.getConnectionName())
                    .dbType(context.getDbType())
                    .status(item.isSuccess() ? "SUCCESS" : "FAIL")
                    .statementType(item.getStatementType())
                    .sqlText(item.getSqlText())
                    .elapsedMs(item.getElapsedMs())
                    .failDetail(item.toFailDetail())
                    .build());
        }
        try {
            client.ingestBatchAsync(events);
        } catch (Exception e) {
            log.warn("提交 SQL 审计上报失败", e);
        }
    }
}
