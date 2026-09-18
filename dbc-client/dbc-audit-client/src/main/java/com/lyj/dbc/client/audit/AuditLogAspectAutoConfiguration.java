package com.lyj.dbc.client.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.BeanFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

/**
 * {@link AuditLog} AOP 装配：仅在 classpath 存在 AspectJ 时生效（需 spring-boot-starter-aop）。
 * <p>
 * 与 {@link AuditClientAutoConfiguration} 拆分，避免 sqlwork 等仅上报场景被强制拉起 AspectJ。
 */
@AutoConfiguration(after = AuditClientAutoConfiguration.class)
@ConditionalOnClass(name = "org.aspectj.lang.annotation.Aspect")
@ConditionalOnProperty(prefix = "dbc.audit.client", name = "enabled", havingValue = "true", matchIfMissing = true)
@EnableAspectJAutoProxy
public class AuditLogAspectAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public AuditLogAspect auditLogAspect(AuditIngestClient ingestClient,
                                         ObjectProvider<ObjectMapper> objectMapper,
                                         BeanFactory beanFactory) {
        return new AuditLogAspect(ingestClient, objectMapper.getIfAvailable(), beanFactory);
    }
}
