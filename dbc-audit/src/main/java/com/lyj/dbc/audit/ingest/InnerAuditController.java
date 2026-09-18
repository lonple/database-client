package com.lyj.dbc.audit.ingest;

import com.lyj.dbc.audit.common.ApiResponse;
import com.lyj.dbc.audit.common.BizException;
import com.lyj.dbc.audit.mtls.MtlsClientContext;
import com.lyj.dbc.client.audit.dto.AuditEventDtos;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * mTLS inner：接收业务服务异步上报的审计事件。
 */
@RestController
@RequestMapping("/inner")
public class InnerAuditController {

    private final AuditIngestService auditIngestService;

    public InnerAuditController(AuditIngestService auditIngestService) {
        this.auditIngestService = auditIngestService;
    }

    @PostMapping("/events")
    public ApiResponse<AuditEventDtos.IngestResult> ingest(@Valid @RequestBody AuditEventDtos.IngestRequest request) {
        String clientId = MtlsClientContext.getClientId();
        if (clientId == null || clientId.isBlank()) {
            throw BizException.forbidden("缺少 mTLS 客户端身份");
        }
        int accepted = auditIngestService.ingest(request);
        return ApiResponse.ok(new AuditEventDtos.IngestResult(accepted));
    }
}
