package com.lyj.dbc.knowledge.knowledge.support;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "dbc.knowledge.graph")
public class AdaGraphProperties {
    /** ada-graph 服务根地址，如 http://127.0.0.1:8101 */
    private String baseUrl = "http://127.0.0.1:8101";
    /** 调用超时（毫秒） */
    private int timeoutMs = 8000;

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public int getTimeoutMs() {
        return timeoutMs;
    }

    public void setTimeoutMs(int timeoutMs) {
        this.timeoutMs = timeoutMs;
    }
}
