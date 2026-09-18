package com.lyj.dbc.audit;

import com.lyj.dbc.client.common.DbcServiceDiscoveryConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.Import;

/**
 * 审计服务启动入口。
 */
@EnableDiscoveryClient
@Import(DbcServiceDiscoveryConfiguration.class)
@SpringBootApplication
public class AuditApplication {

    public static void main(String[] args) {
        SpringApplication.run(AuditApplication.class, args);
    }
}
