package com.lyj.dbc.client.audit;

import com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

/**
 * 审计上报客户端自动装配。若存在 {@link DiscoveryHttpsBaseUrlResolver}，mTLS 基址走 Nacos。
 */
@AutoConfiguration
@EnableConfigurationProperties
@ConditionalOnProperty(prefix = "dbc.audit.client", name = "enabled", havingValue = "true", matchIfMissing = true)
public class AuditClientAutoConfiguration {

    @Bean
    @ConfigurationProperties(prefix = "dbc.audit.client")
    @ConditionalOnMissingBean
    public AuditClientProperties auditClientProperties() {
        return new AuditClientProperties();
    }

    @Bean(destroyMethod = "close")
    @ConditionalOnMissingBean
    public AuditIngestClient auditIngestClient(AuditClientProperties properties,
                                               ObjectProvider<DiscoveryHttpsBaseUrlResolver> discoveryResolver) {
        return new AuditIngestClient(properties, discoveryResolver.getIfAvailable());
    }
}
