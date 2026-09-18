package com.lyj.dbc.manage.bootstrap;

import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.usercenter.UserCenterInnerClient;
import com.lyj.dbc.client.usercenter.dto.PermissionRegisterItem;
import com.lyj.dbc.manage.config.ManageProperties;
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
 * 启动后后台经 usercenter-client（mTLS inner）注册权限并绑定角色。
 */
@Component
@Order(10)
public class PermissionRegisterBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(PermissionRegisterBootstrap.class);

    private static final List<String> ASSET_BIND_ROLES = List.of("SUPER_ADMIN", "SYS_ADMIN", "DB_ADMIN");
    private static final List<String> AUTH_BIND_ROLES = List.of("SUPER_ADMIN", "DB_ADMIN");

    private final ManageProperties properties;
    private final UserCenterInnerClient userCenterInnerClient;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicBoolean registered = new AtomicBoolean(false);
    private volatile Thread worker;

    public PermissionRegisterBootstrap(ManageProperties properties, UserCenterInnerClient userCenterInnerClient) {
        this.properties = properties;
        this.userCenterInnerClient = userCenterInnerClient;
    }

    @Override
    public void run(ApplicationArguments args) {
        worker = new Thread(this::retryLoop, "manage-permission-register");
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
                log.info("manage 权限已注册并绑定角色 asset={} auth={}（第 {} 次尝试）",
                        ASSET_BIND_ROLES, AUTH_BIND_ROLES, attempt);
                return;
            } catch (Exception e) {
                log.warn("manage 权限注册未成功（第 {} 次），{} ms 后重试: {}", attempt, delayMs, e.getMessage());
                log.debug("权限注册失败详情", e);
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
        List<PermissionRegisterItem> assetPermissions = List.of(
                perm("manage.instance.view", "实例查看", "查看实例列表与详情", "manage", "资产管理", "instance", "实例管理", 10),
                perm("manage.instance.operate", "实例操作", "实例增删改、共享与驱动上传", "manage", "资产管理", "instance", "实例管理", 20),
                perm("manage.connection.view", "连接查看", "查看连接列表与详情（密码掩码）", "manage", "资产管理", "connection", "连接管理", 30),
                perm("manage.connection.operate", "连接操作", "连接增删改与改密", "manage", "资产管理", "connection", "连接管理", 40)
        );
        // 权限管控为独立业务模块（module_code=auth），与资产管理（manage）分离
        List<PermissionRegisterItem> authPermissions = List.of(
                perm("auth.workspace.view", "工作空间授权查看", "查看工作空间列表与详情",
                        "auth", "权限管控", "workspace", "工作空间授权", 50),
                perm("auth.workspace.operate", "工作空间授权操作", "创建工作空间、成员、资产挂载与成员授权",
                        "auth", "权限管控", "workspace", "工作空间授权", 60),
                perm("auth.global.policy.view", "全局管控查看", "查看全局管控策略",
                        "auth", "权限管控", "global.policy", "全局管控", 70),
                perm("auth.global.policy.operate", "全局管控操作", "增删改全局管控策略",
                        "auth", "权限管控", "global.policy", "全局管控", 80)
        );
        try {
            userCenterInnerClient.registerPermissions(
                    java.util.stream.Stream.concat(assetPermissions.stream(), authPermissions.stream()).toList());
            userCenterInnerClient.bindPermissionsToRoles(
                    ASSET_BIND_ROLES,
                    assetPermissions.stream().map(PermissionRegisterItem::getCode).toList());
            userCenterInnerClient.bindPermissionsToRoles(
                    AUTH_BIND_ROLES,
                    authPermissions.stream().map(PermissionRegisterItem::getCode).toList());
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
