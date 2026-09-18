package com.lyj.dbc.usercenter.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "dbc.jwt")
public class JwtProperties {

    private String secret;
    private long expireHours = 8;
}
