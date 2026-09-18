package com.lyj.dbc.sqlwork.bootstrap;

import com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import com.lyj.dbc.sqlwork.secrets.SecretFileStore;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import java.io.InputStream;
import java.net.http.HttpClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 启动后后台经 mTLS 向 usercenter 注册 sqlwork 权限并绑定角色。
 * <p>
 * 不阻断进程启动；mTLS 材料缺失时 warn 并指数退避重试。
 */
@Component
@Order(10)
public class PermissionRegisterBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(PermissionRegisterBootstrap.class);

    private static final List<String> BIND_ROLES = List.of("SUPER_ADMIN", "SYS_ADMIN", "DB_ADMIN", "DATA_OPERATOR");

    private final SqlworkProperties properties;
    private final SecretFileStore secretFileStore;
    private final DiscoveryHttpsBaseUrlResolver discoveryHttpsBaseUrlResolver;
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicBoolean registered = new AtomicBoolean(false);
    private volatile Thread worker;

    public PermissionRegisterBootstrap(SqlworkProperties properties,
                                       SecretFileStore secretFileStore,
                                       DiscoveryHttpsBaseUrlResolver discoveryHttpsBaseUrlResolver) {
        this.properties = properties;
        this.secretFileStore = secretFileStore;
        this.discoveryHttpsBaseUrlResolver = discoveryHttpsBaseUrlResolver;
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
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception e) {
                log.warn("sqlwork 权限注册未成功（第 {} 次），{} ms 后重试: {}", attempt, delayMs, e.getMessage());
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

    private void doRegister() throws Exception {
        String clientId = properties.getClientId();
        Path clientP12 = secretFileStore.getSecretsDir().resolve("mtls/clients/" + clientId + ".p12");
        Path clientPassFile = secretFileStore.getSecretsDir().resolve("mtls/clients/" + clientId + ".pass");
        Path trustP12 = secretFileStore.getSecretsDir().resolve("mtls/trust.p12");
        Path trustPassFile = secretFileStore.getSecretsDir().resolve("mtls/ca.pass");
        if (!Files.exists(clientP12) || !Files.exists(clientPassFile)
                || !Files.exists(trustP12) || !Files.exists(trustPassFile)) {
            throw new IllegalStateException(
                    "缺少 mTLS 材料: " + clientP12 + "（需 usercenter 登记并签发客户端证书）");
        }

        RestClient client = buildMtlsRestClient(clientP12, clientPassFile, trustP12, trustPassFile);
        String base = discoveryHttpsBaseUrlResolver.resolveHttpsBaseUrl(properties.getUsercenterMtlsBaseUrl());

        List<Map<String, Object>> permissions = List.of(
                perm("sqlwork.execute", "SQL 执行", "在工作台执行 SQL", "sqlwork", "SQL工作台", "execute", "执行", 10),
                perm("sqlwork.meta.view", "元数据查看", "查看目标库对象树与表列表", "sqlwork", "SQL工作台", "meta", "元数据", 20)
        );
        List<String> permissionCodes = permissions.stream().map(p -> (String) p.get("code")).toList();

        post(client, base + "/inner/permissions/register", Map.of("permissions", permissions));
        post(client, base + "/inner/permissions/bind-roles", Map.of(
                "roleCodes", BIND_ROLES,
                "permissionCodes", permissionCodes
        ));
    }

    private void post(RestClient client, String url, Object body) {
        ApiResponse<Void> resp = client.post()
                .uri(url)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<Void>>() {});
        if (resp == null || resp.getCode() != 0) {
            throw new IllegalStateException("权限注册/绑定失败: " + (resp == null ? "无响应" : resp.getMessage()));
        }
    }

    private RestClient buildMtlsRestClient(Path clientP12, Path clientPassFile, Path trustP12, Path trustPassFile)
            throws Exception {
        char[] clientPass = Files.readString(clientPassFile).trim().toCharArray();
        KeyStore keyStore = KeyStore.getInstance("PKCS12");
        try (InputStream in = Files.newInputStream(clientP12)) {
            keyStore.load(in, clientPass);
        }
        KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        kmf.init(keyStore, clientPass);

        char[] trustPass = Files.readString(trustPassFile).trim().toCharArray();
        KeyStore trustStore = KeyStore.getInstance("PKCS12");
        try (InputStream in = Files.newInputStream(trustP12)) {
            trustStore.load(in, trustPass);
        }
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(trustStore);

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);

        javax.net.ssl.SSLParameters sslParameters = new javax.net.ssl.SSLParameters();
        sslParameters.setEndpointIdentificationAlgorithm(null);

        HttpClient httpClient = HttpClient.newBuilder()
                .sslContext(sslContext)
                .sslParameters(sslParameters)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
        factory.setReadTimeout(Duration.ofSeconds(30));
        return RestClient.builder().requestFactory(factory).build();
    }

    private static Map<String, Object> perm(String code, String name, String description,
                                            String moduleCode, String moduleName,
                                            String featureCode, String featureName, int sortNo) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("code", code);
        m.put("name", name);
        m.put("description", description);
        m.put("moduleCode", moduleCode);
        m.put("moduleName", moduleName);
        m.put("featureCode", featureCode);
        m.put("featureName", featureName);
        m.put("sortNo", sortNo);
        return m;
    }
}
