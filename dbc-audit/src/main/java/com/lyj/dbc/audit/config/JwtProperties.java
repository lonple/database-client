package com.lyj.dbc.audit.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置（与 usercenter / manage 共用密钥）。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.jwt")
public class JwtProperties {

    private String secret;
    private long expireHours = 8;
}
