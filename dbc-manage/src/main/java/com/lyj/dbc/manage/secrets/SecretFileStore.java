package com.lyj.dbc.manage.secrets;

import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.config.SecretsProperties;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 读写 secrets 目录下的密钥文件。
 */
@Component
public class SecretFileStore {

    public static final String FILE_JWT = "jwt-secret.txt";
    public static final String FILE_MANAGE_KEK = "manage-kek.txt";

    private final Path secretsDir;
    private final SecureRandom secureRandom = new SecureRandom();

    public SecretFileStore(SecretsProperties properties) {
        this.secretsDir = Path.of(properties.getDir()).toAbsolutePath().normalize();
    }

    /** secrets 根目录 */
    public Path getSecretsDir() {
        return secretsDir;
    }

    /**
     * 读取文件；不存在则生成随机内容并写入。
     */
    public String readOrCreate(String fileName, int byteLength) {
        ensureDir();
        Path file = secretsDir.resolve(fileName);
        try {
            if (Files.exists(file)) {
                String value = Files.readString(file, StandardCharsets.UTF_8).trim();
                if (!value.isEmpty()) {
                    return value;
                }
            }
            String generated = randomSecret(byteLength);
            Files.writeString(file, generated, StandardCharsets.UTF_8);
            return generated;
        } catch (IOException e) {
            throw BizException.badRequest("读写密钥文件失败: " + file);
        }
    }

    /** 读取已有文件，不存在返回 null */
    public String readIfPresent(String fileName) {
        Path file = secretsDir.resolve(fileName);
        if (!Files.exists(file)) {
            return null;
        }
        try {
            String value = Files.readString(file, StandardCharsets.UTF_8).trim();
            return value.isEmpty() ? null : value;
        } catch (IOException e) {
            throw BizException.badRequest("读取密钥文件失败: " + file);
        }
    }

    /** 覆盖写入明文内容 */
    public void write(String fileName, String content) {
        ensureDir();
        Path file = secretsDir.resolve(fileName);
        try {
            Files.writeString(file, content, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw BizException.badRequest("写入密钥文件失败: " + file);
        }
    }

    private void ensureDir() {
        try {
            Files.createDirectories(secretsDir);
        } catch (IOException e) {
            throw BizException.badRequest("无法创建 secrets 目录: " + secretsDir);
        }
    }

    private String randomSecret(int byteLength) {
        byte[] buf = new byte[byteLength];
        secureRandom.nextBytes(buf);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(buf);
    }
}
