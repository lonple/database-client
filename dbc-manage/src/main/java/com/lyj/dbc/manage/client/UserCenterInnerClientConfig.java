package com.lyj.dbc.manage.client;

import com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.UserCenterInnerClientProperties;
import com.lyj.dbc.manage.config.ManageProperties;
import com.lyj.dbc.manage.secrets.SecretFileStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 装配可复用的 usercenter inner 客户端（Nacos discovery:// + mTLS）。
 */
@Configuration
public class UserCenterInnerClientConfig {

    @Bean
    public UserCenterInnerClient userCenterInnerClient(ManageProperties properties,
                                                       SecretFileStore secretFileStore,
                                                       DiscoveryHttpsBaseUrlResolver discoveryResolver) {
        return new UserCenterInnerClient(UserCenterInnerClientProperties.builder()
                .mtlsBaseUrl(properties.getUsercenterMtlsBaseUrl())
                .clientId(properties.getClientId())
                .secretsDir(secretFileStore.getSecretsDir())
                .build(), discoveryResolver);
    }
}
