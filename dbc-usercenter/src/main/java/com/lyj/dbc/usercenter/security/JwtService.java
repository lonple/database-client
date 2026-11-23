package com.lyj.dbc.usercenter.security;

import com.lyj.dbc.usercenter.config.AuthProperties;
import com.lyj.dbc.usercenter.config.JwtProperties;
import com.lyj.dbc.usercenter.secrets.SecretFileStore;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 用户 JWT 签发与解析；密钥来自 secrets/jwt-secret.txt。
 */
@Component
public class JwtService {

    public static final String TYP_ACCESS = "access";
    public static final String TYP_REFRESH = "refresh";

    private final AuthProperties authProperties;
    private final SecretKey key;
    private final JwtDenyListService denyListService;

    public JwtService(JwtProperties properties, AuthProperties authProperties,
                      SecretFileStore secretFileStore, JwtDenyListService denyListService) {
        this.authProperties = authProperties;
        this.denyListService = denyListService;
        String secret = secretFileStore.readOrCreate(SecretFileStore.FILE_JWT, 48);
        properties.setSecret(secret);
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public IssuedToken createAccessToken(LoginUser user) {
        return issue(user, TYP_ACCESS, Duration.ofMinutes(authProperties.getAccessTtlMinutes()));
    }

    public IssuedToken createRefreshToken(LoginUser user) {
        return issue(user, TYP_REFRESH, Duration.ofHours(authProperties.getRefreshTtlHours()));
    }

    private IssuedToken issue(LoginUser user, String typ, Duration ttl) {
        Instant now = Instant.now();
        Instant exp = now.plus(ttl);
        String jti = UUID.randomUUID().toString().replace("-", "");
        String roleCodes = user.getRoleCodes() == null ? "" :
                user.getRoleCodes().stream().collect(Collectors.joining(","));
        String token = Jwts.builder()
                .id(jti)
                .subject(String.valueOf(user.getUserId()))
                .claim("username", user.getUsername())
                .claim("roleCodes", roleCodes)
                .claim("roleCode", roleCodes.contains(",") ? roleCodes.split(",")[0] : roleCodes)
                .claim("typ", typ)
                .issuedAt(Date.from(now))
                .expiration(Date.from(exp))
                .signWith(key)
                .compact();
        return new IssuedToken(token, jti, ttl, exp);
    }

    /** 解析 access；校验 typ 与拒绝名单。 */
    public LoginUser parseAccess(String token) {
        Claims claims = parseClaims(token, TYP_ACCESS);
        return toUser(claims);
    }

    /** 解析 refresh；校验 typ 与拒绝名单。 */
    public Claims parseRefreshClaims(String token) {
        return parseClaims(token, TYP_REFRESH);
    }

    public LoginUser toUser(Claims claims) {
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

    public void denyToken(String token) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
            denyClaims(claims);
        } catch (Exception ignored) {
            // 已过期或无效：无需再吊销
        }
    }

    public void denyClaims(Claims claims) {
        String jti = claims.getId();
        Date exp = claims.getExpiration();
        if (jti == null || exp == null) {
            return;
        }
        Duration ttl = Duration.between(Instant.now(), exp.toInstant());
        if (!ttl.isNegative() && !ttl.isZero()) {
            denyListService.deny(jti, ttl);
        }
    }

    public long accessExpireSeconds() {
        return authProperties.getAccessTtlMinutes() * 60;
    }

    public Duration refreshTtl() {
        return Duration.ofHours(authProperties.getRefreshTtlHours());
    }

    private Claims parseClaims(String token, String expectedTyp) {
        Claims claims = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        String typ = claims.get("typ", String.class);
        if (!expectedTyp.equals(typ)) {
            throw new IllegalArgumentException("令牌类型不匹配");
        }
        String jti = claims.getId();
        if (denyListService.isDenied(jti)) {
            throw new IllegalArgumentException("令牌已失效");
        }
        return claims;
    }

    public record IssuedToken(String token, String jti, Duration ttl, Instant expiresAt) {
    }
}
