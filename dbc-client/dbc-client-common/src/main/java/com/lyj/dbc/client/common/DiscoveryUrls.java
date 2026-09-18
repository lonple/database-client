package com.lyj.dbc.client.common;

/**
 * 服务发现 URL 约定：{@code discovery://{spring.application.name}}。
 * <p>
 * 由 {@code DiscoveryHttpsBaseUrlResolver} 解析为 {@code https://host:mtls-port}（端口来自 Nacos metadata）。
 */
public final class DiscoveryUrls {

    public static final String PREFIX = "discovery://";
    public static final String MTLS_PORT_METADATA = "mtls-port";

    private DiscoveryUrls() {
    }

    public static boolean isDiscoveryUrl(String url) {
        return url != null && url.startsWith(PREFIX);
    }

    public static String serviceId(String discoveryUrl) {
        if (!isDiscoveryUrl(discoveryUrl)) {
            throw new IllegalArgumentException("not a discovery url: " + discoveryUrl);
        }
        String id = discoveryUrl.substring(PREFIX.length()).trim();
        while (id.endsWith("/")) {
            id = id.substring(0, id.length() - 1);
        }
        if (id.isEmpty()) {
            throw new IllegalArgumentException("empty service id in discovery url");
        }
        return id;
    }

    public static String ofService(String serviceId) {
        return PREFIX + serviceId;
    }
}
