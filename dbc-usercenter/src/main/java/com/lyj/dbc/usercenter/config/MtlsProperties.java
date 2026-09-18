package com.lyj.dbc.usercenter.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * mTLS 服务端口配置。
 */
@Data
@Component
@ConfigurationProperties(prefix = "dbc.mtls")
public class MtlsProperties {

    /** 是否启用 mTLS 端口 */
    private boolean enabled = true;

    /** HTTPS + 客户端证书端口 */
    private int port = 8044;
}
