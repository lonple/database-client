package com.lyj.dbc.usercenter.mtls;

import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.secrets.SecretFileStore;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.asn1.x509.BasicConstraints;
import org.bouncycastle.asn1.x509.Extension;
import org.bouncycastle.asn1.x509.GeneralName;
import org.bouncycastle.asn1.x509.GeneralNames;
import org.bouncycastle.asn1.x509.KeyUsage;
import org.bouncycastle.cert.X509CertificateHolder;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.operator.ContentSigner;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;

/**
 * 本地 CA 与应用/服务端证书签发（开发与内网）。
 * <p>
 * 签发时机：用户中心启动补齐、应用登记立即签发、管理端重签覆盖。
 * 算法：BouncyCastle + RSA-2048；应用证书 CN 必须等于 clientId。
 * 多实例共用同一应用客户端证书；ECDSA 业务签名密钥按 instanceId 另管。
 */
@Component
public class MtlsCertificateService {

    private static final String CA_P12 = "mtls/ca.p12";
    private static final String CA_CRT = "mtls/ca.crt";
    private static final String CA_PASS_FILE = "mtls/ca.pass";
    /** 仅含 CA 证书条目的信任库（Tomcat mTLS 要求 TrustedCertificateEntry，不能直接用含私钥的 ca.p12） */
    private static final String TRUST_P12 = "mtls/trust.p12";
    private static final String SERVER_P12 = "mtls/server.p12";
    private static final String SERVER_PASS_FILE = "mtls/server.pass";
    private static final String CLIENT_DIR = "mtls/clients";

    private final SecretFileStore secretFileStore;
    private final SecureRandom secureRandom = new SecureRandom();

    public MtlsCertificateService(SecretFileStore secretFileStore) {
        this.secretFileStore = secretFileStore;
    }

    /** 确保 CA、信任库与 server 证书存在 */
    public synchronized void ensureCaAndServer() {
        Path caP12 = path(CA_P12);
        if (!Files.exists(caP12)) {
            createCa();
        }
        ensureTrustStore();
        Path serverP12 = path(SERVER_P12);
        if (!Files.exists(serverP12)) {
            issueServerCert();
        }
    }

    /** 确保应用客户端证书存在 */
    public synchronized void ensureClientCert(String clientId) {
        ensureCaAndServer();
        Path clientP12 = clientP12Path(clientId);
        if (!Files.exists(clientP12)) {
            issueClientCert(clientId);
        }
    }

    /** 重新签发应用客户端证书 */
    public synchronized void reissueClientCert(String clientId) {
        ensureCaAndServer();
        issueClientCert(clientId);
    }

    public Path clientP12Path(String clientId) {
        return path(CLIENT_DIR + "/" + clientId + ".p12");
    }

    public Path clientPassPath(String clientId) {
        return path(CLIENT_DIR + "/" + clientId + ".pass");
    }

    public char[] clientPass(String clientId) {
        String pass = secretFileStore.readIfPresent(CLIENT_DIR + "/" + clientId + ".pass");
        if (pass == null || pass.isBlank()) {
            throw BizException.badRequest("缺少客户端证书密码文件: " + clientId);
        }
        return pass.toCharArray();
    }

    public Path serverP12Path() {
        return path(SERVER_P12);
    }

    public char[] serverPass() {
        return readPass(SERVER_PASS_FILE);
    }

    public Path trustStorePath() {
        return path(TRUST_P12);
    }

    public char[] trustStorePass() {
        return readPass(CA_PASS_FILE);
    }

    private void createCa() {
        try {
            KeyPair pair = genRsa();
            String pass = randomPass();
            X509Certificate cert = selfSign(pair, "CN=DBC-Local-CA", true, 3650);
            writeP12(path(CA_P12), pass, "ca", pair.getPrivate(), cert);
            secretFileStore.write(CA_PASS_FILE, pass);
            Files.write(path(CA_CRT), cert.getEncoded());
            writeTrustStore(cert, pass);
        } catch (Exception e) {
            throw BizException.badRequest("创建 mTLS CA 失败: " + e.getMessage());
        }
    }

    /** 从已有 CA 补齐仅含证书条目的信任库（兼容旧版只生成了 ca.p12 的目录） */
    private void ensureTrustStore() {
        Path trustP12 = path(TRUST_P12);
        if (Files.exists(trustP12)) {
            return;
        }
        try {
            CaMaterial ca = loadCa();
            writeTrustStore(ca.cert(), new String(readPass(CA_PASS_FILE)));
        } catch (Exception e) {
            throw BizException.badRequest("创建 mTLS 信任库失败: " + e.getMessage());
        }
    }

    private void writeTrustStore(X509Certificate caCert, String pass) throws Exception {
        Files.createDirectories(path(TRUST_P12).getParent());
        KeyStore ks = KeyStore.getInstance("PKCS12");
        ks.load(null, null);
        ks.setCertificateEntry("ca", caCert);
        try (OutputStream out = Files.newOutputStream(path(TRUST_P12))) {
            ks.store(out, pass.toCharArray());
        }
    }

    private void issueServerCert() {
        try {
            CaMaterial ca = loadCa();
            KeyPair pair = genRsa();
            String pass = randomPass();
            // SAN 含 Docker Compose 服务名与 host.docker.internal，便于容器内 mTLS
            X509Certificate cert = signWithCa(ca, pair, "CN=dbc-usercenter-mtls", false, 825,
                    new GeneralNames(new GeneralName[]{
                            new GeneralName(GeneralName.dNSName, "localhost"),
                            new GeneralName(GeneralName.dNSName, "host.docker.internal"),
                            new GeneralName(GeneralName.dNSName, "dbc-usercenter"),
                            new GeneralName(GeneralName.dNSName, "dbc-audit"),
                            new GeneralName(GeneralName.iPAddress, "127.0.0.1")
                    }));
            writeP12(path(SERVER_P12), pass, "server", pair.getPrivate(), cert, ca.cert());
            secretFileStore.write(SERVER_PASS_FILE, pass);
        } catch (Exception e) {
            throw BizException.badRequest("签发 mTLS 服务端证书失败: " + e.getMessage());
        }
    }

    private void issueClientCert(String clientId) {
        try {
            Files.createDirectories(path(CLIENT_DIR));
            CaMaterial ca = loadCa();
            KeyPair pair = genRsa();
            String pass = randomPass();
            X509Certificate cert = signWithCa(ca, pair, "CN=" + clientId, false, 825, null);
            writeP12(clientP12Path(clientId), pass, clientId, pair.getPrivate(), cert, ca.cert());
            secretFileStore.write(CLIENT_DIR + "/" + clientId + ".pass", pass);
        } catch (Exception e) {
            throw BizException.badRequest("签发客户端证书失败: " + e.getMessage());
        }
    }

    private CaMaterial loadCa() throws Exception {
        char[] pass = readPass(CA_PASS_FILE);
        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (InputStream in = Files.newInputStream(path(CA_P12))) {
            ks.load(in, pass);
        }
        String alias = ks.aliases().nextElement();
        PrivateKey key = (PrivateKey) ks.getKey(alias, pass);
        X509Certificate cert = (X509Certificate) ks.getCertificate(alias);
        return new CaMaterial(key, cert);
    }

    private X509Certificate selfSign(KeyPair pair, String dn, boolean ca, int days) throws Exception {
        Instant now = Instant.now();
        X500Name name = new X500Name(dn);
        JcaX509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
                name, new BigInteger(160, secureRandom),
                Date.from(now.minus(1, ChronoUnit.DAYS)),
                Date.from(now.plus(days, ChronoUnit.DAYS)),
                name, pair.getPublic());
        builder.addExtension(Extension.basicConstraints, true, new BasicConstraints(ca));
        if (ca) {
            builder.addExtension(Extension.keyUsage, true,
                    new KeyUsage(KeyUsage.keyCertSign | KeyUsage.cRLSign));
        }
        ContentSigner signer = new JcaContentSignerBuilder("SHA256WithRSA").build(pair.getPrivate());
        X509CertificateHolder holder = builder.build(signer);
        return new JcaX509CertificateConverter().getCertificate(holder);
    }

    private X509Certificate signWithCa(CaMaterial ca, KeyPair subject, String dn, boolean isCa, int days,
                                       GeneralNames san) throws Exception {
        Instant now = Instant.now();
        X500Name issuer = new X500Name(ca.cert().getSubjectX500Principal().getName());
        X500Name subjectName = new X500Name(dn);
        JcaX509v3CertificateBuilder builder = new JcaX509v3CertificateBuilder(
                issuer, new BigInteger(160, secureRandom),
                Date.from(now.minus(1, ChronoUnit.DAYS)),
                Date.from(now.plus(days, ChronoUnit.DAYS)),
                subjectName, subject.getPublic());
        builder.addExtension(Extension.basicConstraints, true, new BasicConstraints(isCa));
        builder.addExtension(Extension.keyUsage, true,
                new KeyUsage(KeyUsage.digitalSignature | KeyUsage.keyEncipherment));
        if (san != null) {
            builder.addExtension(Extension.subjectAlternativeName, false, san);
        }
        ContentSigner signer = new JcaContentSignerBuilder("SHA256WithRSA").build(ca.key());
        return new JcaX509CertificateConverter().getCertificate(builder.build(signer));
    }

    private void writeP12(Path file, String pass, String alias, PrivateKey key, X509Certificate... chain)
            throws Exception {
        Files.createDirectories(file.getParent());
        KeyStore ks = KeyStore.getInstance("PKCS12");
        ks.load(null, null);
        ks.setKeyEntry(alias, key, pass.toCharArray(), chain);
        try (OutputStream out = Files.newOutputStream(file)) {
            ks.store(out, pass.toCharArray());
        }
    }

    private KeyPair genRsa() throws Exception {
        KeyPairGenerator gen = KeyPairGenerator.getInstance("RSA");
        gen.initialize(2048);
        return gen.generateKeyPair();
    }

    private String randomPass() {
        byte[] buf = new byte[16];
        secureRandom.nextBytes(buf);
        StringBuilder sb = new StringBuilder();
        for (byte b : buf) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private char[] readPass(String relative) {
        String pass = secretFileStore.readIfPresent(relative);
        if (pass == null || pass.isBlank()) {
            throw BizException.badRequest("缺少证书密码文件: " + relative);
        }
        return pass.toCharArray();
    }

    private Path path(String relative) {
        return secretFileStore.getSecretsDir().resolve(relative).normalize();
    }

    private record CaMaterial(PrivateKey key, X509Certificate cert) {
    }
}
