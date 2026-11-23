package com.lyj.dbc.gateway.security;

import com.lyj.dbc.gateway.config.SecretsProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 网关侧 access JWT 验签（与 usercenter 共用 jwt-secret.txt）。
 */
@Component
public class GatewayJwtService {

    public static final String TYP_ACCESS = "access";

    private final SecretKey key;

    public GatewayJwtService(SecretsProperties secretsProperties) {
        Path file = Path.of(secretsProperties.getDir()).toAbsolutePath().normalize().resolve("jwt-secret.txt");
        if (!Files.isRegularFile(file)) {
            throw new IllegalStateException("JWT 密钥文件不存在: " + file + "，请与 usercenter 共用 secrets/jwt-secret.txt");
        }
        try {
            String secret = Files.readString(file, StandardCharsets.UTF_8).trim();
            if (secret.length() < 32) {
                throw new IllegalStateException("JWT 密钥长度不足");
            }
            this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new IllegalStateException("读取 JWT 密钥失败: " + file, e);
        }
    }

    public Claims parseAccess(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        if (!TYP_ACCESS.equals(claims.get("typ", String.class))) {
            throw new IllegalArgumentException("令牌类型不匹配");
        }
        return claims;
    }
}
