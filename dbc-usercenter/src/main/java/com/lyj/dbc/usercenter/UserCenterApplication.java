package com.lyj.dbc.usercenter;

import com.lyj.dbc.client.common.DbcServiceDiscoveryConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.context.annotation.Import;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableDiscoveryClient
@Import(DbcServiceDiscoveryConfiguration.class)
@EnableScheduling
@SpringBootApplication
public class UserCenterApplication {

    public static void main(String[] args) {
        SpringApplication.run(UserCenterApplication.class, args);
    }
}
