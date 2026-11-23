package com.lyj.dbc.sqlwork.security;

import com.lyj.dbc.sqlwork.config.JwtProperties;
import com.lyj.dbc.sqlwork.secrets.SecretFileStore;
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

    public static final String TYP_ACCESS = "access";

    private final JwtProperties properties;
    private final SecretKey key;
    private final JwtDenyListService denyListService;

    public JwtService(JwtProperties properties, SecretFileStore secretFileStore,
                      JwtDenyListService denyListService) {
        this.properties = properties;
        this.denyListService = denyListService;
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
        if (!TYP_ACCESS.equals(claims.get("typ", String.class))) {
            throw new IllegalArgumentException("令牌类型不匹配");
        }
        if (denyListService.isDenied(claims.getId())) {
            throw new IllegalArgumentException("令牌已失效");
        }
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
