package com.lyj.dbc.client.common;

import org.springframework.cloud.client.loadbalancer.LoadBalancerClient;
import org.springframework.cloud.client.loadbalancer.LoadBalanced;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

/**
 * 业务服务间调用：HTTP 走 {@code @LoadBalanced RestClient}；mTLS 基址走 Nacos {@code mtls-port} metadata。
 * <p>
 * 在各业务启动类上 {@code @Import(DbcServiceDiscoveryConfiguration.class)}。
 */
@Configuration
public class DbcServiceDiscoveryConfiguration {

    @Bean
    @LoadBalanced
    public RestClient.Builder loadBalancedRestClientBuilder() {
        return RestClient.builder();
    }

    @Bean
    public DiscoveryHttpsBaseUrlResolver discoveryHttpsBaseUrlResolver(LoadBalancerClient loadBalancerClient) {
        return new LoadBalancerDiscoveryHttpsBaseUrlResolver(loadBalancerClient);
    }
}
