package com.lyj.dbc.usercenter.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 浏览器会话：双令牌 TTL 与 Cookie 属性。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.auth")
public class AuthProperties {

    /** access JWT 有效期（分钟） */
    private long accessTtlMinutes = 30;

    /** refresh JWT 有效期（小时） */
    private long refreshTtlHours = 8;

    private final Cookie cookie = new Cookie();

    @Data
    public static class Cookie {
        /** 生产应为 true；本地 HTTP 开发默认 false */
        private boolean secure = false;
        /** Lax / Strict / None */
        private String sameSite = "Lax";
        private String refreshName = "dbc_refresh";
        private String csrfName = "dbc_csrf";
        /**
         * refresh Cookie Path（浏览器所见路径，含网关前缀）。
         */
        private String refreshPath = "/dbc-usercenter/auth";
        private String csrfPath = "/";
    }
}
