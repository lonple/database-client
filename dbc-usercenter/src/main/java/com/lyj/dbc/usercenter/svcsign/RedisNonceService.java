package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.config.SvcSignProperties;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * 基于 Redis 的 nonce 去重（分布式防重放）。
 */
@Component
public class RedisNonceService {

    private final StringRedisTemplate redisTemplate;
    private final SvcSignProperties properties;

    public RedisNonceService(StringRedisTemplate redisTemplate, SvcSignProperties properties) {
        this.redisTemplate = redisTemplate;
        this.properties = properties;
    }

    /**
     * 尝试占用 nonce；已存在则判定为重放。
     * Redis 异常时 fail-closed。
     */
    public void consumeOrReject(String verifierClientId, String callerClientId, String nonce) {
        String key = "dbc:nonce:" + verifierClientId + ":" + callerClientId + ":" + nonce;
        try {
            Boolean ok = redisTemplate.opsForValue()
                    .setIfAbsent(key, "1", Duration.ofSeconds(properties.getNonceTtlSeconds()));
            if (ok == null || !ok) {
                throw BizException.unauthorized("请求重放或 nonce 无效");
            }
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw BizException.unauthorized("防重放服务不可用");
        }
    }
}
