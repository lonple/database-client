package com.lyj.dbc.usercenter.mtls;

import com.lyj.dbc.usercenter.config.MtlsProperties;
import org.apache.catalina.connector.Connector;
import org.apache.coyote.http11.Http11NioProtocol;
import org.apache.tomcat.util.net.SSLHostConfig;
import org.apache.tomcat.util.net.SSLHostConfigCertificate;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.stereotype.Component;

/**
 * 在原有 HTTP 之外增加 mTLS HTTPS 端口。
 */
@Component
public class MtlsTomcatCustomizer implements WebServerFactoryCustomizer<TomcatServletWebServerFactory> {

    private final MtlsProperties mtlsProperties;
    private final MtlsCertificateService certificateService;

    public MtlsTomcatCustomizer(MtlsProperties mtlsProperties, MtlsCertificateService certificateService) {
        this.mtlsProperties = mtlsProperties;
        this.certificateService = certificateService;
    }

    @Override
    public void customize(TomcatServletWebServerFactory factory) {
        if (!mtlsProperties.isEnabled()) {
            return;
        }
        certificateService.ensureCaAndServer();
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
        sslHostConfig.setTruststoreFile(certificateService.trustStorePath().toString());
        sslHostConfig.setTruststorePassword(new String(certificateService.trustStorePass()));
        sslHostConfig.setTruststoreType("PKCS12");

        SSLHostConfigCertificate cert = new SSLHostConfigCertificate(sslHostConfig, SSLHostConfigCertificate.Type.RSA);
        cert.setCertificateKeystoreFile(certificateService.serverP12Path().toString());
        cert.setCertificateKeystorePassword(new String(certificateService.serverPass()));
        cert.setCertificateKeystoreType("PKCS12");
        sslHostConfig.addCertificate(cert);

        protocol.addSslHostConfig(sslHostConfig);
        return connector;
    }
}
