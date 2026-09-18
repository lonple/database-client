package com.lyj.dbc.audit.es;

import com.lyj.dbc.audit.config.AuditProperties;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/**
 * 审计 ES 索引名：{@code {indexEnv}-dbc-audit-biz-yyyy.MM} / {@code ...-sql-yyyy.MM}。
 */
@Component
public class AuditIndexNames {

    private static final DateTimeFormatter MONTH = DateTimeFormatter.ofPattern("yyyy.MM")
            .withZone(ZoneOffset.UTC);

    private final String indexEnv;

    public AuditIndexNames(AuditProperties properties) {
        this.indexEnv = properties.getIndexEnv() == null || properties.getIndexEnv().isBlank()
                ? "dev"
                : properties.getIndexEnv().trim();
    }

    public String bizIndex(Instant occurredAt) {
        Instant t = occurredAt == null ? Instant.now() : occurredAt;
        return indexEnv + "-dbc-audit-biz-" + MONTH.format(t);
    }

    public String sqlIndex(Instant occurredAt) {
        Instant t = occurredAt == null ? Instant.now() : occurredAt;
        return indexEnv + "-dbc-audit-sql-" + MONTH.format(t);
    }

    /** 业务日志检索通配索引 */
    public String bizSearchPattern() {
        return indexEnv + "-dbc-audit-biz-*";
    }

    /** SQL 日志检索通配索引 */
    public String sqlSearchPattern() {
        return indexEnv + "-dbc-audit-sql-*";
    }
}
