package com.lyj.dbc.audit.mtls;

import com.lyj.dbc.audit.common.BizException;
import com.lyj.dbc.audit.secrets.SecretFileStore;
import org.springframework.stereotype.Component;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 读取已有 mTLS 材料（不签发、不生成证书）。
 * <p>
 * 依赖 usercenter 已落盘：{@code secrets/mtls/server.p12}、{@code server.pass}、
 * {@code trust.p12}、{@code ca.pass}。
 */
@Component
public class MtlsMaterialStore {

    private static final String SERVER_P12 = "mtls/server.p12";
    private static final String SERVER_PASS = "mtls/server.pass";
    private static final String TRUST_P12 = "mtls/trust.p12";
    private static final String CA_PASS = "mtls/ca.pass";

    private final SecretFileStore secretFileStore;

    public MtlsMaterialStore(SecretFileStore secretFileStore) {
        this.secretFileStore = secretFileStore;
    }

    /** 校验必备材料已存在，缺失则抛业务异常 */
    public void requirePresent() {
        Path serverP12 = serverP12Path();
        Path trustP12 = trustStorePath();
        if (!Files.exists(serverP12) || !Files.exists(trustP12)) {
            throw BizException.badRequest("缺少 mTLS 材料（server.p12 / trust.p12），请先启动 usercenter 签发");
        }
        if (secretFileStore.readIfPresent(SERVER_PASS) == null
                || secretFileStore.readIfPresent(CA_PASS) == null) {
            throw BizException.badRequest("缺少 mTLS 密码文件（server.pass / ca.pass）");
        }
    }

    public Path serverP12Path() {
        return secretFileStore.getSecretsDir().resolve(SERVER_P12);
    }

    public char[] serverPass() {
        return readPass(SERVER_PASS);
    }

    public Path trustStorePath() {
        return secretFileStore.getSecretsDir().resolve(TRUST_P12);
    }

    public char[] trustStorePass() {
        return readPass(CA_PASS);
    }

    private char[] readPass(String relative) {
        String pass = secretFileStore.readIfPresent(relative);
        if (pass == null || pass.isBlank()) {
            throw BizException.badRequest("缺少 mTLS 密码文件: " + relative);
        }
        return pass.toCharArray();
    }
}
