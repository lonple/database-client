package com.lyj.dbc.knowledge.knowledge.milvus;

import io.milvus.v2.client.ConnectConfig;
import io.milvus.v2.client.MilvusClientV2;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;

@Configuration
@EnableConfigurationProperties(MilvusProperties.class)
public class MilvusConfig {
    private static final Logger log = LoggerFactory.getLogger(MilvusConfig.class);

    private MilvusClientV2 client;

    @Bean
    @ConditionalOnProperty(prefix = "dbc.knowledge.milvus", name = "enabled", havingValue = "true", matchIfMissing = true)
    public MilvusClientV2 milvusClientV2(MilvusProperties props) {
        ConnectConfig.ConnectConfigBuilder builder = ConnectConfig.builder()
                .uri(props.getUri());
        if (StringUtils.hasText(props.getToken())) {
            builder.token(props.getToken());
        }
        this.client = new MilvusClientV2(builder.build());
        log.info("Milvus client connected uri={} collection={}", props.getUri(), props.getCollection());
        return this.client;
    }

    @PreDestroy
    public void close() {
        if (client != null) {
            try {
                client.close(5);
            } catch (Exception e) {
                log.warn("close milvus client: {}", e.getMessage());
            }
        }
    }
}
