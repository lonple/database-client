package com.lyj.dbc.knowledge.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Service
public class JwtDenyListService {
    private static final Logger log = LoggerFactory.getLogger(JwtDenyListService.class);
    private static final String KEY_PREFIX = "dbc:jwt:deny:";

    private final StringRedisTemplate redisTemplate;

    public JwtDenyListService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public boolean isDenied(String jti) {
        if (jti == null || jti.isBlank()) {
            return true;
        }
        try {
            return Boolean.TRUE.equals(redisTemplate.hasKey(KEY_PREFIX + jti));
        } catch (Exception e) {
            log.error("查询 JWT 拒绝名单失败 jti={}", jti, e);
            return true;
        }
    }
}
