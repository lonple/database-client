package com.lyj.dbc.knowledge.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "dbc.secrets")
public class SecretsProperties {
    private String dir = "secrets";
}
