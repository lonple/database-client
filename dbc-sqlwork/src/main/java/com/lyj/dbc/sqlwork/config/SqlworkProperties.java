package com.lyj.dbc.sqlwork.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * sqlwork 服务业务配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.sqlwork")
public class SqlworkProperties {

    /** manage HTTP 基址（Nacos 服务名，如 http://dbc-manage） */
    private String manageBaseUrl = "http://dbc-manage";

    /** 本服务 clientId，对应 mTLS 客户端证书 */
    private String clientId = "dbc-sqlwork";

    /** 执行默认最大返回行数 */
    private int executeMaxRows = 1000;

    /** 执行结果行数硬上限 */
    private int executeMaxRowsCap = 5000;

    /** 语句查询超时（秒） */
    private int executeTimeoutSeconds = 30;

    /** 单批最多语句数 */
    private int executeMaxStatements = 50;

    /** 按连接缓存的 Druid 最大池大小（maxActive） */
    private int poolMaxSize = 5;

    /** 每用户最多工作台会话数 */
    private int sessionMaxPerUser = 10;

    /** 无事务会话闲置 TTL（秒） */
    private int sessionIdleTtlSeconds = 1800;

    /** 事务中会话闲置 TTL（秒）；超时 rollback 并释放租约 */
    private int sessionTransactionIdleTtlSeconds = 900;

    /** 会话清理扫描间隔（毫秒） */
    private long sessionCleanupIntervalMs = 30000L;

    /** usercenter mTLS：discovery://dbc-usercenter */
    private String usercenterMtlsBaseUrl = "discovery://dbc-usercenter";

    /** 权限注册首次重试间隔（毫秒） */
    private long permissionRegisterInitialDelayMs = 2000L;

    /** 权限注册最大重试间隔（毫秒） */
    private long permissionRegisterMaxDelayMs = 60000L;
}
