package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.client.common.DiscoveryUrls;
import com.lyj.dbc.client.common.MtlsRestClientFactory;
import com.lyj.dbc.usercenter.app.dto.AppKeyApplyRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyHeartbeatRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyRotateRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeySignRequest;
import com.lyj.dbc.usercenter.app.vo.AppKeySignResultVO;
import com.lyj.dbc.usercenter.app.vo.AppKeyVO;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.config.MtlsProperties;
import com.lyj.dbc.usercenter.config.SvcSignProperties;
import com.lyj.dbc.usercenter.mtls.MtlsCertificateService;
import com.lyj.dbc.usercenter.secrets.SecretFileStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import java.io.InputStream;
import java.net.http.HttpClient;
import java.nio.file.Files;
import java.security.KeyStore;
import java.time.Duration;
import java.util.UUID;

/**
 * 经本机 mTLS 回环调用用户中心：申请密钥、代签、心跳、轮换。
 * <p>
 * 设计约定：usercenter 自身代签走 {@code https://127.0.0.1:{mtls-port}}，不经 Nacos
 *（避免启动时尚无可用实例 / 自注册竞态）。其它服务调 usercenter 仍用 {@code discovery://dbc-usercenter}。
 */
@Component
@Order(2)
public class CenterSignClient implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(CenterSignClient.class);

    private final SvcSignProperties properties;
    private final MtlsProperties mtlsProperties;
    private final SecretFileStore secretFileStore;
    private final MtlsCertificateService certificateService;
    private final String instanceId;
    private final String mtlsBaseUrl;
    private RestTemplate restTemplate;

    private volatile String currentKid;

    public CenterSignClient(SvcSignProperties properties, MtlsProperties mtlsProperties,
                            SecretFileStore secretFileStore,
                            MtlsCertificateService certificateService) {
        this.properties = properties;
        this.mtlsProperties = mtlsProperties;
        this.secretFileStore = secretFileStore;
        this.certificateService = certificateService;
        this.instanceId = resolveInstanceId();
        this.mtlsBaseUrl = resolveSelfMtlsBaseUrl();
    }

    @Override
    public void run(ApplicationArguments args) {
        certificateService.ensureClientCert(properties.getClientId());
        this.restTemplate = buildMtlsRestTemplate();
        AppKeyVO vo = apply();
        currentKid = vo.getKid();
        log.info("已通过 mTLS 申请签名密钥 instanceId={} kid={} baseUrl={}", instanceId, currentKid, mtlsBaseUrl);
    }

    public String instanceId() {
        return instanceId;
    }

    public String kid() {
        return currentKid;
    }

    public String clientId() {
        return properties.getClientId();
    }

    public AppKeyVO apply() {
        AppKeyApplyRequest req = new AppKeyApplyRequest();
        req.setInstanceId(instanceId);
        AppKeyVO vo = post("/inner/apps/keys/apply", req, new ParameterizedTypeReference<ApiResponse<AppKeyVO>>() {});
        currentKid = vo.getKid();
        return vo;
    }

    public AppKeyVO rotate() {
        AppKeyRotateRequest req = new AppKeyRotateRequest();
        req.setInstanceId(instanceId);
        AppKeyVO vo = post("/inner/apps/keys/rotate", req, new ParameterizedTypeReference<ApiResponse<AppKeyVO>>() {});
        currentKid = vo.getKid();
        return vo;
    }

    public AppKeySignResultVO sign(String method, String path, String query, String timestamp,
                                   String nonce, byte[] body) {
        AppKeySignRequest req = new AppKeySignRequest();
        req.setInstanceId(instanceId);
        req.setMethod(method);
        req.setPath(path);
        req.setQuery(query);
        req.setTimestamp(timestamp);
        req.setNonce(nonce);
        req.setBodySha256Hex(SignCanonical.sha256Hex(body == null ? new byte[0] : body));
        return post("/inner/apps/keys/sign", req, new ParameterizedTypeReference<ApiResponse<AppKeySignResultVO>>() {});
    }

    @Scheduled(fixedDelayString = "${dbc.svc-sign.heartbeat-interval-ms:30000}")
    public void heartbeat() {
        if (restTemplate == null) {
            return;
        }
        try {
            AppKeyHeartbeatRequest req = new AppKeyHeartbeatRequest();
            req.setInstanceId(instanceId);
            post("/inner/apps/keys/heartbeat", req, new ParameterizedTypeReference<ApiResponse<Void>>() {});
        } catch (Exception e) {
            log.warn("签名密钥心跳失败 instanceId={}", instanceId, e);
        }
    }

    private <T> T post(String path, Object body, ParameterizedTypeReference<ApiResponse<T>> type) {
        ensureRestTemplate();
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        ResponseEntity<ApiResponse<T>> resp = restTemplate.exchange(
                mtlsBaseUrl + path,
                HttpMethod.POST, new HttpEntity<>(body, headers), type);
        ApiResponse<T> api = resp.getBody();
        if (api == null || api.getCode() != 0) {
            throw BizException.unauthorized(api == null ? "代签服务无响应" : api.getMessage());
        }
        return api.getData();
    }

    private void ensureRestTemplate() {
        if (restTemplate == null) {
            certificateService.ensureClientCert(properties.getClientId());
            restTemplate = buildMtlsRestTemplate();
        }
    }

    /**
     * 本机回环；若配置了绝对 https URL 则用之；discovery:// 一律忽略并回退回环（启动竞态不安全）。
     */
    private String resolveSelfMtlsBaseUrl() {
        String configured = properties.getMtlsBaseUrl();
        if (configured != null && !configured.isBlank()) {
            String trimmed = configured.trim();
            if (DiscoveryUrls.isDiscoveryUrl(trimmed)) {
                log.warn("dbc.svc-sign.mtls-base-url={} 不适用于 usercenter 自身代签，改用本机回环", trimmed);
            } else {
                return MtlsRestClientFactory.trimTrailingSlash(trimmed);
            }
        }
        return "https://127.0.0.1:" + mtlsProperties.getPort();
    }

    private RestTemplate buildMtlsRestTemplate() {
        try {
            char[] clientPass = certificateService.clientPass(properties.getClientId());
            KeyStore keyStore = KeyStore.getInstance("PKCS12");
            try (InputStream in = Files.newInputStream(certificateService.clientP12Path(properties.getClientId()))) {
                keyStore.load(in, clientPass);
            }
            KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
            kmf.init(keyStore, clientPass);

            char[] trustPass = certificateService.trustStorePass();
            KeyStore trustStore = KeyStore.getInstance("PKCS12");
            try (InputStream in = Files.newInputStream(certificateService.trustStorePath())) {
                trustStore.load(in, trustPass);
            }
            TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
            tmf.init(trustStore);

            SSLContext sslContext = SSLContext.getInstance("TLS");
            sslContext.init(kmf.getKeyManagers(), MtlsRestClientFactory.caChainOnlyTrustManagers(tmf), null);

            HttpClient httpClient = HttpClient.newBuilder()
                    .sslContext(sslContext)
                    .connectTimeout(Duration.ofSeconds(5))
                    .build();
            JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
            factory.setReadTimeout(Duration.ofSeconds(15));
            return new RestTemplate(factory);
        } catch (Exception e) {
            throw new IllegalStateException("初始化 mTLS RestTemplate 失败", e);
        }
    }

    private String resolveInstanceId() {
        String file = properties.getClientId() + ".instance";
        String existing = secretFileStore.readIfPresent(file);
        if (existing != null && !existing.isBlank()) {
            return existing.trim();
        }
        String id = UUID.randomUUID().toString().replace("-", "");
        secretFileStore.write(file, id);
        return id;
    }
}
