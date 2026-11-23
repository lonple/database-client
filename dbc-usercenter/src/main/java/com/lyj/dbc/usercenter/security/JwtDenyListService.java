package com.lyj.dbc.usercenter.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;

/**
 * JWT jti 拒绝名单（登出 / 轮换作废）。Redis 异常 fail-closed。
 */
@Service
public class JwtDenyListService {

    private static final Logger log = LoggerFactory.getLogger(JwtDenyListService.class);
    private static final String KEY_PREFIX = "dbc:jwt:deny:";

    private final StringRedisTemplate redisTemplate;

    public JwtDenyListService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void deny(String jti, Duration ttl) {
        if (jti == null || jti.isBlank() || ttl == null || ttl.isNegative() || ttl.isZero()) {
            return;
        }
        try {
            redisTemplate.opsForValue().set(KEY_PREFIX + jti, "1", ttl);
        } catch (Exception e) {
            log.error("写入 JWT 拒绝名单失败 jti={}", jti, e);
            throw new IllegalStateException("令牌吊销失败", e);
        }
    }

    public boolean isDenied(String jti) {
        if (jti == null || jti.isBlank()) {
            return true;
        }
        try {
            Boolean has = redisTemplate.hasKey(KEY_PREFIX + jti);
            return Boolean.TRUE.equals(has);
        } catch (Exception e) {
            log.error("查询 JWT 拒绝名单失败 jti={}", jti, e);
            return true;
        }
    }
}
