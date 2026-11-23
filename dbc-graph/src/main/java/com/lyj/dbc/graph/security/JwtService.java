package com.lyj.dbc.graph.security;

import com.lyj.dbc.graph.config.JwtProperties;
import com.lyj.dbc.graph.secrets.SecretFileStore;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

@Component
public class JwtService {
    public static final String TYP_ACCESS = "access";

    private final SecretKey key;
    private final JwtDenyListService denyListService;

    public JwtService(JwtProperties properties, SecretFileStore secretFileStore, JwtDenyListService denyListService) {
        this.denyListService = denyListService;
        String secret = secretFileStore.readOrCreate(SecretFileStore.FILE_JWT, 48);
        properties.setSecret(secret);
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public LoginUser parse(String token) {
        Claims claims = Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
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
        return LoginUser.of(Long.valueOf(claims.getSubject()), claims.get("username", String.class), roleCodes);
    }
}
