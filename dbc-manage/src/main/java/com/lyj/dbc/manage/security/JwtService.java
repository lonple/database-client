package com.lyj.dbc.manage.security;

import com.lyj.dbc.manage.config.JwtProperties;
import com.lyj.dbc.manage.secrets.SecretFileStore;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;
import java.util.stream.Collectors;

/**
 * 用户 JWT 签发与解析；密钥来自 secrets/jwt-secret.txt（与 usercenter 共用）。
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

    public String createToken(LoginUser user) {
        Instant now = Instant.now();
        Instant exp = now.plus(properties.getExpireHours(), ChronoUnit.HOURS);
        String roleCodes = user.getRoleCodes() == null ? "" :
                user.getRoleCodes().stream().collect(Collectors.joining(","));
        return Jwts.builder()
                .subject(String.valueOf(user.getUserId()))
                .claim("username", user.getUsername())
                .claim("roleCodes", roleCodes)
                .claim("roleCode", roleCodes.contains(",") ? roleCodes.split(",")[0] : roleCodes)
                .issuedAt(Date.from(now))
                .expiration(Date.from(exp))
                .signWith(key)
                .compact();
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
        return LoginUser.of(
                Long.valueOf(claims.getSubject()),
                claims.get("username", String.class),
                roleCodes
        );
    }

    public long expireSeconds() {
        return properties.getExpireHours() * 3600;
    }
}
