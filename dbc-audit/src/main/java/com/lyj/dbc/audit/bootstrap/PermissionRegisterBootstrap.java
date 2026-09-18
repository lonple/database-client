package com.lyj.dbc.audit.bootstrap;

import com.lyj.dbc.audit.config.AuditProperties;
import com.lyj.dbc.audit.security.PermissionCodes;
import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.dto.PermissionRegisterItem;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 启动后后台经 usercenter-client（mTLS inner）注册审计权限并绑定角色。
 */
@Component
@Order(10)
public class PermissionRegisterBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(PermissionRegisterBootstrap.class);

    private static final List<String> BIND_ROLES = List.of("SUPER_ADMIN", "SYS_ADMIN");

    private final AuditProperties properties;
    private final UserCenterInnerClient userCenterInnerClient;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicBoolean registered = new AtomicBoolean(false);
    private volatile Thread worker;

    public PermissionRegisterBootstrap(AuditProperties properties, UserCenterInnerClient userCenterInnerClient) {
        this.properties = properties;
        this.userCenterInnerClient = userCenterInnerClient;
    }

    @Override
    public void run(ApplicationArguments args) {
        worker = new Thread(this::retryLoop, "audit-permission-register");
        worker.setDaemon(true);
        worker.start();
    }

    public boolean isRegistered() {
        return registered.get();
    }

    @PreDestroy
    public void shutdown() {
        running.set(false);
        Thread t = worker;
        if (t != null) {
            t.interrupt();
        }
    }

    private void retryLoop() {
        long delayMs = Math.max(1000L, properties.getPermissionRegisterInitialDelayMs());
        long maxDelayMs = Math.max(delayMs, properties.getPermissionRegisterMaxDelayMs());
        int attempt = 0;
        while (running.get() && !registered.get()) {
            attempt++;
            try {
                doRegister();
                registered.set(true);
                log.info("audit 权限已注册并绑定角色 {}（第 {} 次尝试）", BIND_ROLES, attempt);
                return;
            } catch (Exception e) {
                // 启动补偿重试：只记摘要，不打栈（usercenter 未就绪属常态）
                log.info("audit 权限注册未成功（第 {} 次）：{}，{} ms 后重试",
                        attempt, e.getMessage(), delayMs);
            }
            try {
                Thread.sleep(delayMs);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            delayMs = Math.min(maxDelayMs, delayMs * 2);
        }
    }

    private void doRegister() {
        List<PermissionRegisterItem> permissions = List.of(
                perm(PermissionCodes.AUDIT_BIZ_VIEW, "业务日志查看", "查看业务操作审计列表与详情",
                        "audit", "审计日志", "biz", "业务日志", 10),
                perm(PermissionCodes.AUDIT_SQL_VIEW, "SQL日志查看", "查看 SQL 操作审计列表与详情",
                        "audit", "审计日志", "sql", "SQL操作日志", 20)
        );
        try {
            userCenterInnerClient.registerPermissions(permissions);
            userCenterInnerClient.bindPermissionsToRoles(
                    BIND_ROLES,
                    permissions.stream().map(PermissionRegisterItem::getCode).toList());
        } catch (InnerClientException e) {
            throw e;
        }
    }

    private static PermissionRegisterItem perm(String code, String name, String description,
                                               String moduleCode, String moduleName,
                                               String featureCode, String featureName, int sortNo) {
        return PermissionRegisterItem.builder()
                .code(code)
                .name(name)
                .description(description)
                .moduleCode(moduleCode)
                .moduleName(moduleName)
                .featureCode(featureCode)
                .featureName(featureName)
                .sortNo(sortNo)
                .build();
    }
}
