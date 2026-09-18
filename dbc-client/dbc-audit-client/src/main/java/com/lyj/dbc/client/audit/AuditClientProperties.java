package com.lyj.dbc.client.audit;

import lombok.Data;

/**
 * 审计上报客户端配置。
 */
@Data
public class AuditClientProperties {

    /** 是否启用（关闭则全部 no-op） */
    private boolean enabled = true;

    /** audit mTLS：discovery://dbc-audit（Nacos）或 https://host:port 逃生舱 */
    private String mtlsBaseUrl = "discovery://dbc-audit";

    /** 本服务 clientId（对应 secrets/mtls/clients/{id}.p12） */
    private String clientId = "dbc-sqlwork";

    /** secrets 根目录（相对进程工作目录或绝对路径） */
    private String secretsDir = "secrets";

    /** 异步发送线程数 */
    private int asyncPoolSize = 4;

    /** 异步队列容量；满则丢弃并打 warn */
    private int queueCapacity = 10000;

    /** 单条 SQL 正文安全上限（字节，按 UTF-8） */
    private int sqlMaxBytes = 1_048_576;
}
