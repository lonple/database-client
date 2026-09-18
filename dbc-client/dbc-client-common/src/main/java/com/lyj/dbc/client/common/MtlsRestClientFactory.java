package com.lyj.dbc.client.common;

import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509ExtendedTrustManager;
import javax.net.ssl.X509TrustManager;
import java.io.InputStream;
import java.net.Socket;
import java.net.http.HttpClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyStore;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.time.Duration;
import java.util.Objects;

/**
 * 基于 secrets 目录下 mTLS 材料构建 RestClient（调 usercenter / audit mTLS 端口）。
 * <p>
 * 信任：校验对端证书由本 CA 签发；不校验主机名/IP（Nacos 常返回实例 IP，SAN 为服务名）。
 */
public final class MtlsRestClientFactory {

    private MtlsRestClientFactory() {
    }

    /**
     * @param secretsDir 仓库 secrets 根目录
     * @param clientId   本应用 clientId（对应 clients/{clientId}.p12）
     */
    public static RestClient create(Path secretsDir, String clientId) {
        Objects.requireNonNull(secretsDir, "secretsDir");
        Objects.requireNonNull(clientId, "clientId");
        try {
            Path clientP12 = secretsDir.resolve("mtls/clients/" + clientId + ".p12");
            Path clientPassFile = secretsDir.resolve("mtls/clients/" + clientId + ".pass");
            Path trustP12 = secretsDir.resolve("mtls/trust.p12");
            Path trustPassFile = secretsDir.resolve("mtls/ca.pass");
            if (!Files.exists(clientP12) || !Files.exists(clientPassFile)
                    || !Files.exists(trustP12) || !Files.exists(trustPassFile)) {
                throw new InnerClientException("缺少 mTLS 材料: " + clientP12);
            }

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
            sslContext.init(kmf.getKeyManagers(), caChainOnlyTrustManagers(tmf), null);

            HttpClient httpClient = HttpClient.newBuilder()
                    .sslContext(sslContext)
                    .connectTimeout(Duration.ofSeconds(5))
                    .build();
            JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(httpClient);
            factory.setReadTimeout(Duration.ofSeconds(30));
            return RestClient.builder().requestFactory(factory).build();
        } catch (InnerClientException e) {
            throw e;
        } catch (Exception e) {
            throw new InnerClientException("构建 mTLS RestClient 失败", e);
        }
    }

    /**
     * 委托 PKIX 验链，但绕过 {@code X509TrustManagerImpl} 基于 Socket/SSLEngine 的主机名/IP 身份校验。
     * JDK HttpClient 在 {@code checkServerTrusted(..., SSLEngine)} 路径会做 SAN 匹配，
     * {@code setEndpointIdentificationAlgorithm(null)} 不足以关闭该行为。
     */
    public static TrustManager[] caChainOnlyTrustManagers(TrustManagerFactory tmf) {
        X509TrustManager delegate = null;
        for (TrustManager tm : tmf.getTrustManagers()) {
            if (tm instanceof X509TrustManager x509) {
                delegate = x509;
                break;
            }
        }
        if (delegate == null) {
            throw new InnerClientException("TrustManagerFactory 未提供 X509TrustManager");
        }
        final X509TrustManager pkix = delegate;
        return new TrustManager[]{new X509ExtendedTrustManager() {
            @Override
            public void checkClientTrusted(X509Certificate[] chain, String authType) throws CertificateException {
                pkix.checkClientTrusted(chain, authType);
            }

            @Override
            public void checkServerTrusted(X509Certificate[] chain, String authType) throws CertificateException {
                pkix.checkServerTrusted(chain, authType);
            }

            @Override
            public X509Certificate[] getAcceptedIssuers() {
                return pkix.getAcceptedIssuers();
            }

            @Override
            public void checkClientTrusted(X509Certificate[] chain, String authType, Socket socket)
                    throws CertificateException {
                pkix.checkClientTrusted(chain, authType);
            }

            @Override
            public void checkServerTrusted(X509Certificate[] chain, String authType, Socket socket)
                    throws CertificateException {
                pkix.checkServerTrusted(chain, authType);
            }

            @Override
            public void checkClientTrusted(X509Certificate[] chain, String authType, SSLEngine engine)
                    throws CertificateException {
                pkix.checkClientTrusted(chain, authType);
            }

            @Override
            public void checkServerTrusted(X509Certificate[] chain, String authType, SSLEngine engine)
                    throws CertificateException {
                pkix.checkServerTrusted(chain, authType);
            }
        }};
    }

    public static String trimTrailingSlash(String url) {
        if (url == null || url.isBlank()) {
            return url;
        }
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
