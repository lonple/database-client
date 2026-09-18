package com.lyj.dbc.client.common;

import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.loadbalancer.LoadBalancerClient;

import java.util.Objects;

/**
 * 通过 Spring Cloud LoadBalancer 选实例，用 Nacos metadata {@code mtls-port} 拼 HTTPS 基址。
 * <p>
 * 若传入已是 {@code https://...} / {@code http://...} 绝对地址，则原样返回（本地排障逃生舱）。
 */
public class LoadBalancerDiscoveryHttpsBaseUrlResolver implements DiscoveryHttpsBaseUrlResolver {

    private final LoadBalancerClient loadBalancerClient;

    public LoadBalancerDiscoveryHttpsBaseUrlResolver(LoadBalancerClient loadBalancerClient) {
        this.loadBalancerClient = Objects.requireNonNull(loadBalancerClient, "loadBalancerClient");
    }

    @Override
    public String resolveHttpsBaseUrl(String discoveryOrAbsoluteUrl) {
        if (discoveryOrAbsoluteUrl == null || discoveryOrAbsoluteUrl.isBlank()) {
            throw new InnerClientException("服务地址为空");
        }
        String raw = discoveryOrAbsoluteUrl.trim();
        if (!DiscoveryUrls.isDiscoveryUrl(raw)) {
            return MtlsRestClientFactory.trimTrailingSlash(raw);
        }
        String serviceId = DiscoveryUrls.serviceId(raw);
        ServiceInstance instance = loadBalancerClient.choose(serviceId);
        if (instance == null) {
            throw new InnerClientException("Nacos 无可用实例: " + serviceId);
        }
        String mtlsPort = firstMetadata(instance, DiscoveryUrls.MTLS_PORT_METADATA, "mtls.port");
        if (mtlsPort == null || mtlsPort.isBlank()) {
            throw new InnerClientException("实例缺少 metadata mtls-port: " + serviceId
                    + " host=" + instance.getHost());
        }
        return "https://" + instance.getHost() + ":" + mtlsPort.trim();
    }

    private static String firstMetadata(ServiceInstance instance, String... keys) {
        if (instance.getMetadata() == null) {
            return null;
        }
        for (String key : keys) {
            String v = instance.getMetadata().get(key);
            if (v != null && !v.isBlank()) {
                return v;
            }
        }
        return null;
    }
}
