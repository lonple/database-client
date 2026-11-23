package com.lyj.dbc.usercenter.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

/**
 * CORS Origin 白名单（禁止 * + credentials）。逗号分隔，便于环境变量覆盖。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.cors")
public class CorsProperties {

    /** 如 http://127.0.0.1:8005,http://localhost:8005 */
    private String allowedOriginPatterns = "http://127.0.0.1:8005,http://localhost:8005";

    public List<String> resolvedOriginPatterns() {
        if (allowedOriginPatterns == null || allowedOriginPatterns.isBlank()) {
            return List.of();
        }
        return Arrays.stream(allowedOriginPatterns.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }
}
