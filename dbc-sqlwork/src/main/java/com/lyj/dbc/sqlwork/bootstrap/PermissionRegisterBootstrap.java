package com.lyj.dbc.sqlwork.bootstrap;

import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.dto.PermissionRegisterItem;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
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
 * 启动后后台经 usercenter-client（mTLS inner）注册 sqlwork 权限并绑定角色。
 * <p>
 * 不阻断进程启动；usercenter 未就绪或 mTLS 材料缺失时 warn 并指数退避重试。
 */
@Component
@Order(10)
public class PermissionRegisterBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(PermissionRegisterBootstrap.class);

    private static final List<String> BIND_ROLES = List.of("SUPER_ADMIN", "SYS_ADMIN", "DB_ADMIN", "DATA_OPERATOR");

    private final SqlworkProperties properties;
    private final UserCenterInnerClient userCenterInnerClient;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicBoolean registered = new AtomicBoolean(false);
    private volatile Thread worker;

    public PermissionRegisterBootstrap(SqlworkProperties properties,
                                       UserCenterInnerClient userCenterInnerClient) {
        this.properties = properties;
        this.userCenterInnerClient = userCenterInnerClient;
    }

    @Override
    public void run(ApplicationArguments args) {
        worker = new Thread(this::retryLoop, "sqlwork-permission-register");
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
                log.info("sqlwork 权限已注册并绑定角色 {}（第 {} 次尝试）", BIND_ROLES, attempt);
                return;
            } catch (Exception e) {
                log.warn("sqlwork 权限注册未成功（第 {} 次），{} ms 后重试", attempt, delayMs, e);
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
                perm("sqlwork.execute", "SQL 执行", "在工作台执行 SQL",
                        "sqlwork", "SQL工作台", "execute", "执行", 10),
                perm("sqlwork.meta.view", "元数据查看", "查看目标库对象树与表列表",
                        "sqlwork", "SQL工作台", "meta", "元数据", 20)
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
