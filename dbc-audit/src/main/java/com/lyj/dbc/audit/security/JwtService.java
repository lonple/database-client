package com.lyj.dbc.audit.security;

import com.lyj.dbc.audit.config.JwtProperties;
import com.lyj.dbc.audit.secrets.SecretFileStore;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

/**
 * 用户 JWT 解析；密钥来自 secrets/jwt-secret.txt（与 usercenter / manage 共用）。
 */
@Component
public class JwtService {

    private final JwtProperties properties;
    private final SecretKey key;

    public JwtService(JwtProperties properties, SecretFileStore secretFileStore) {
        this.properties = properties;
        String secret = secretFileStore.readOrCreate(SecretFileStore.FILE_JWT, 48);
        properties.setSecret(secret);
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public LoginUser parse(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        String roleCodes = claims.get("roleCodes", String.class);
        if (roleCodes == null || roleCodes.isBlank()) {
            roleCodes = claims.get("roleCode", String.class);
        }
        String permissions = claims.get("permissions", String.class);
        return LoginUser.of(
                Long.valueOf(claims.getSubject()),
                claims.get("username", String.class),
                roleCodes,
                permissions
        );
    }

    public long expireSeconds() {
        return properties.getExpireHours() * 3600;
    }

    /** 将权限列表序列化为 CSV（签发扩展用） */
    public static String joinCsv(java.util.List<String> values) {
        if (values == null || values.isEmpty()) {
            return "";
        }
        return values.stream().collect(Collectors.joining(","));
    }
}
