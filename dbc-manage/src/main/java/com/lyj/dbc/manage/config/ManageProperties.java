package com.lyj.dbc.manage.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * manage 服务业务配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.manage")
public class ManageProperties {

    /** 驱动 JAR 落盘目录（相对工作目录或绝对路径） */
    private String driverDir = "secrets/manage/drivers";

    /** usercenter HTTP 基址（Bearer；Nacos 服务名，如 http://dbc-usercenter） */
    private String usercenterBaseUrl = "http://dbc-usercenter";

    /** usercenter mTLS：discovery://服务名 或 https://host:port 逃生舱 */
    private String usercenterMtlsBaseUrl = "discovery://dbc-usercenter";

    /**
     * sqlwork HTTP 基址（Nacos 服务名，如 http://dbc-sqlwork）。
     */
    private String sqlworkBaseUrl = "http://dbc-sqlwork";

    /** 本服务 clientId，对应 mTLS 客户端证书 */
    private String clientId = "dbc-manage";

    /** 驱动文件大小上限（字节） */
    private long driverMaxBytes = 64L * 1024 * 1024;

    /** 权限注册首次重试间隔（毫秒） */
    private long permissionRegisterInitialDelayMs = 2000L;

    /** 权限注册最大重试间隔（毫秒，指数退避封顶） */
    private long permissionRegisterMaxDelayMs = 60000L;

    /** 工作空间授权 Redis 缓存（见详设 §6.7） */
    private AuthzCache authzCache = new AuthzCache();

    @Data
    public static class AuthzCache {
        private boolean enabled = true;
        /** 空间资产 HASH TTL（秒），命中续期 */
        private long assetsTtlSeconds = 1200L;
        /** 用户授权 STRING TTL（秒），命中续期 */
        private long userTtlSeconds = 600L;
        /** 版本号 / uids SET TTL（秒） */
        private long verTtlSeconds = 86400L;
    }
}