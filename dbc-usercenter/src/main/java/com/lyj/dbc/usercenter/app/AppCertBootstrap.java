package com.lyj.dbc.usercenter.app;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 启动时签发 CA / 服务端证书，并为已登记应用补齐客户端证书。
 */
@Component
@Order(1)
public class AppCertBootstrap implements ApplicationRunner {

    private final AppService appService;

    public AppCertBootstrap(AppService appService) {
        this.appService = appService;
    }

    @Override
    public void run(ApplicationArguments args) {
        appService.ensureAllClientCerts();
    }
}
