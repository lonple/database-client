package com.lyj.dbc.audit.api;

import com.lyj.dbc.audit.common.ApiResponse;
import com.lyj.dbc.audit.common.PageResult;
import com.lyj.dbc.audit.es.AuditDocument;
import com.lyj.dbc.audit.es.AuditEsService;
import com.lyj.dbc.audit.security.PermissionCodes;
import com.lyj.dbc.audit.security.RequirePermission;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;

/**
 * 业务操作审计日志查询。
 */
@RestController
@RequestMapping("/biz-logs")
public class BizLogController {

    private final AuditEsService auditEsService;

    public BizLogController(AuditEsService auditEsService) {
        this.auditEsService = auditEsService;
    }

    @GetMapping
    @RequirePermission(PermissionCodes.AUDIT_BIZ_VIEW)
    public ApiResponse<PageResult<AuditDocument>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(required = false) String operatorUsername,
            @RequestParam(required = false) String module,
            @RequestParam(required = false) String action,
            @RequestParam(required = false) String result,
            @RequestParam(required = false) String keyword) {
        return ApiResponse.ok(auditEsService.searchBiz(
                page, size, from, to, operatorUsername, module, action, result, keyword));
    }

    @GetMapping("/{eventId}")
    @RequirePermission(PermissionCodes.AUDIT_BIZ_VIEW)
    public ApiResponse<AuditDocument> detail(@PathVariable String eventId) {
        return ApiResponse.ok(auditEsService.getBizById(eventId));
    }
}
