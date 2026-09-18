package com.lyj.dbc.usercenter.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 服务间请求签名相关配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.svc-sign")
public class SvcSignProperties {

    /** 本服务内置 clientId */
    private String clientId = "dbc-usercenter";

    /**
     * 自身代签基址：空或 discovery:// 时回环 {@code https://127.0.0.1:{dbc.mtls.port}}；
     * 仅允许配置绝对 {@code https://...} 覆盖（排障）。
     */
    private String mtlsBaseUrl = "";

    /** 时间戳允许偏差（秒） */
    private long timestampSkewSeconds = 300;

    /** Redis nonce TTL（秒） */
    private long nonceTtlSeconds = 300;

    /** 心跳间隔（毫秒） */
    private long heartbeatIntervalMs = 30000;

    /** 心跳失活阈值（秒） */
    private long heartbeatStaleSeconds = 90;

    /** 公钥缓存刷新间隔（毫秒） */
    private long publicKeyRefreshMs = 30000;

    /** 单应用允许的未失活 active kid 上限 */
    private int maxActiveKidsPerApp = 32;
}
