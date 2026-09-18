package com.lyj.dbc.audit.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * audit 服务业务配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.audit")
public class AuditProperties {

    /** ES 索引环境前缀，如 dev / staging / prod */
    private String indexEnv = "dev";

    /** usercenter HTTP 基址（Nacos 服务名） */
    private String usercenterBaseUrl = "http://dbc-usercenter";

    /** usercenter mTLS：discovery://dbc-usercenter */
    private String usercenterMtlsBaseUrl = "discovery://dbc-usercenter";

    /** 本服务 clientId，对应 mTLS 客户端证书 */
    private String clientId = "dbc-audit";

    /** 权限注册首次重试间隔（毫秒） */
    private long permissionRegisterInitialDelayMs = 2000L;

    /** 权限注册最大重试间隔（毫秒，指数退避封顶） */
    private long permissionRegisterMaxDelayMs = 60000L;
}
