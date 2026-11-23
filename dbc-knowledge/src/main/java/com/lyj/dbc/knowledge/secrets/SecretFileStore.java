package com.lyj.dbc.knowledge.secrets;

import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.config.SecretsProperties;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.Base64;

@Component
public class SecretFileStore {
    public static final String FILE_JWT = "jwt-secret.txt";

    private final Path secretsDir;
    private final SecureRandom secureRandom = new SecureRandom();

    public SecretFileStore(SecretsProperties properties) {
        this.secretsDir = Path.of(properties.getDir()).toAbsolutePath().normalize();
    }

    public String readOrCreate(String fileName, int byteLength) {
        try {
            Files.createDirectories(secretsDir);
            Path file = secretsDir.resolve(fileName);
            if (Files.exists(file)) {
                String value = Files.readString(file, StandardCharsets.UTF_8).trim();
                if (!value.isEmpty()) {
                    return value;
                }
            }
            byte[] buf = new byte[byteLength];
            secureRandom.nextBytes(buf);
            String generated = Base64.getUrlEncoder().withoutPadding().encodeToString(buf);
            Files.writeString(file, generated, StandardCharsets.UTF_8);
            return generated;
        } catch (IOException e) {
            throw new BizException("读写密钥文件失败: " + fileName);
        }
    }
}
