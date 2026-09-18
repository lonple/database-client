package com.lyj.dbc.client.common;

/**
 * 将 {@code discovery://服务名} 解析为可拨号的 HTTPS 基址（含 mTLS 端口）。
 */
@FunctionalInterface
public interface DiscoveryHttpsBaseUrlResolver {

    /**
     * @param discoveryOrAbsoluteUrl {@code discovery://dbc-usercenter} 或完整 {@code https://host:port}
     * @return 无尾斜杠的 HTTPS 基址
     */
    String resolveHttpsBaseUrl(String discoveryOrAbsoluteUrl);
}
