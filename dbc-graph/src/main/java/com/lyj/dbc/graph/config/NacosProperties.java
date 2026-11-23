package com.lyj.dbc.graph.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "dbc.nacos")
public class NacosProperties {
    private String serverAddr = "127.0.0.1:8000";
    /** 留空则自动选择非回环 IPv4，本地可设 127.0.0.1。 */
    private String advertiseHost = "";
}
