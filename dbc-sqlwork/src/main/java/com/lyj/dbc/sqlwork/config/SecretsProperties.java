package com.lyj.dbc.sqlwork.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * secrets 目录配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.secrets")
public class SecretsProperties {

    /** secrets 目录路径（相对工作目录或绝对路径；默认仓库根下 secrets/） */
    private String dir = "secrets";
}
