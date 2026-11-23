package com.lyj.dbc.gateway.security;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 浏览器入口：校验 Bearer access JWT（login/refresh/logout 与健康检查除外）。
 * 见详设「网关与注册中心」§7。
 */
@Component
public class AccessJwtGatewayFilter implements GlobalFilter, Ordered {

    private final GatewayJwtService jwtService;
    private final JwtDenyListService denyListService;
    private final ObjectMapper objectMapper;

    public AccessJwtGatewayFilter(GatewayJwtService jwtService, JwtDenyListService denyListService,
                                  ObjectMapper objectMapper) {
        this.jwtService = jwtService;
        this.denyListService = denyListService;
        this.objectMapper = objectMapper;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (HttpMethod.OPTIONS.equals(exchange.getRequest().getMethod())) {
            return chain.filter(exchange);
        }
        String path = exchange.getRequest().getURI().getPath();
        if (isPublic(path)) {
            return chain.filter(exchange);
        }
        String header = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            return unauthorized(exchange.getResponse(), "未登录或令牌无效");
        }
        String token = header.substring(7).trim();
        final Claims claims;
        try {
            claims = jwtService.parseAccess(token);
        } catch (Exception e) {
            return unauthorized(exchange.getResponse(), "未登录或令牌无效");
        }
        return denyListService.isDenied(claims.getId())
                .flatMap(denied -> {
                    if (Boolean.TRUE.equals(denied)) {
                        return unauthorized(exchange.getResponse(), "未登录或令牌无效");
                    }
                    return chain.filter(exchange);
                });
    }

    private static boolean isPublic(String path) {
        if (path == null) {
            return false;
        }
        if (path.startsWith("/actuator/health") || path.startsWith("/actuator/info")) {
            return true;
        }
        return path.endsWith("/auth/login")
                || path.endsWith("/auth/refresh")
                || path.endsWith("/auth/logout");
    }

    private Mono<Void> unauthorized(ServerHttpResponse response, String message) {
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] body;
        try {
            // Map.of 不允许 null value；data 固定为 null 须用可变 Map
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("code", 401);
            payload.put("message", message != null ? message : "未登录或令牌无效");
            payload.put("data", null);
            body = objectMapper.writeValueAsBytes(payload);
        } catch (JsonProcessingException e) {
            body = ("{\"code\":401,\"message\":\"未登录或令牌无效\",\"data\":null}")
                    .getBytes(StandardCharsets.UTF_8);
        }
        DataBuffer buffer = response.bufferFactory().wrap(body);
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
