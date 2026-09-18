package com.lyj.dbc.audit.client;

import com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.UserCenterInnerClientProperties;
import com.lyj.dbc.audit.config.AuditProperties;
import com.lyj.dbc.audit.secrets.SecretFileStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class UserCenterInnerClientConfig {

    @Bean
    public UserCenterInnerClient userCenterInnerClient(AuditProperties properties,
                                                       SecretFileStore secretFileStore,
                                                       DiscoveryHttpsBaseUrlResolver discoveryResolver) {
        return new UserCenterInnerClient(UserCenterInnerClientProperties.builder()
                .mtlsBaseUrl(properties.getUsercenterMtlsBaseUrl())
                .clientId(properties.getClientId())
                .secretsDir(secretFileStore.getSecretsDir())
                .build(), discoveryResolver);
    }
}
