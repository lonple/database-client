package com.lyj.dbc.audit.mtls;

import com.lyj.dbc.audit.config.MtlsProperties;
import org.apache.catalina.connector.Connector;
import org.apache.coyote.http11.Http11NioProtocol;
import org.apache.tomcat.util.net.SSLHostConfig;
import org.apache.tomcat.util.net.SSLHostConfigCertificate;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.stereotype.Component;

/**
 * 在原有 HTTP 之外增加 mTLS HTTPS 端口（仅读取已有证书，不生成）。
 */
@Component
public class MtlsTomcatCustomizer implements WebServerFactoryCustomizer<TomcatServletWebServerFactory> {

    private final MtlsProperties mtlsProperties;
    private final MtlsMaterialStore materialStore;

    public MtlsTomcatCustomizer(MtlsProperties mtlsProperties, MtlsMaterialStore materialStore) {
        this.mtlsProperties = mtlsProperties;
        this.materialStore = materialStore;
    }

    @Override
    public void customize(TomcatServletWebServerFactory factory) {
        if (!mtlsProperties.isEnabled()) {
            return;
        }
        materialStore.requirePresent();
        factory.addAdditionalTomcatConnectors(httpsConnector());
    }

    private Connector httpsConnector() {
        Connector connector = new Connector(Http11NioProtocol.class.getName());
        connector.setScheme("https");
        connector.setSecure(true);
        connector.setPort(mtlsProperties.getPort());

        Http11NioProtocol protocol = (Http11NioProtocol) connector.getProtocolHandler();
        protocol.setSSLEnabled(true);

        SSLHostConfig sslHostConfig = new SSLHostConfig();
        sslHostConfig.setProtocols("TLSv1.2+TLSv1.3");
        sslHostConfig.setCertificateVerification("required");
        sslHostConfig.setTruststoreFile(materialStore.trustStorePath().toString());
        sslHostConfig.setTruststorePassword(new String(materialStore.trustStorePass()));
        sslHostConfig.setTruststoreType("PKCS12");

        SSLHostConfigCertificate cert = new SSLHostConfigCertificate(sslHostConfig, SSLHostConfigCertificate.Type.RSA);
        cert.setCertificateKeystoreFile(materialStore.serverP12Path().toString());
        cert.setCertificateKeystorePassword(new String(materialStore.serverPass()));
        cert.setCertificateKeystoreType("PKCS12");
        sslHostConfig.addCertificate(cert);

        protocol.addSslHostConfig(sslHostConfig);
        return connector;
    }
}
