package com.lyj.dbc.client.audit;

import com.lyj.dbc.client.audit.dto.AuditEventDtos;

import java.util.List;

/**
 * 审计事件发布端口（便于单测替换；生产由 {@link AuditIngestClient} 实现）。
 */
public interface AuditEventPublisher {

    void ingestAsync(AuditEventDtos.AuditEvent event);

    void ingestBatchAsync(List<AuditEventDtos.AuditEvent> events);
}
