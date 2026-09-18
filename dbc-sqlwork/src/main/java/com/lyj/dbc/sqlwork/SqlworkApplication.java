package com.lyj.dbc.sqlwork;

import com.lyj.dbc.client.common.DbcServiceDiscoveryConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.Import;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * SQL 工作台执行面启动入口。
 */
@EnableDiscoveryClient
@Import(DbcServiceDiscoveryConfiguration.class)
@EnableScheduling
@SpringBootApplication
public class SqlworkApplication {

    public static void main(String[] args) {
        SpringApplication.run(SqlworkApplication.class, args);
    }
}
