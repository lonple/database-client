package com.lyj.dbc.gateway.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/**
 * 网关侧 JWT jti 拒绝名单查询。Redis 异常 fail-closed。
 */
@Service
public class JwtDenyListService {

    private static final Logger log = LoggerFactory.getLogger(JwtDenyListService.class);
    private static final String KEY_PREFIX = "dbc:jwt:deny:";

    private final ReactiveStringRedisTemplate redisTemplate;

    public JwtDenyListService(ReactiveStringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public Mono<Boolean> isDenied(String jti) {
        if (jti == null || jti.isBlank()) {
            return Mono.just(true);
        }
        return redisTemplate.hasKey(KEY_PREFIX + jti)
                .onErrorResume(e -> {
                    log.error("查询 JWT 拒绝名单失败 jti={}", jti, e);
                    return Mono.just(true);
                });
    }
}
