package com.lyj.dbc.manage.authz.cache;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.manage.config.ManageProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * 工作空间资产 / 成员授权 Redis 缓存。删缓存失败不重试，依赖 TTL。
 */
@Service
public class WorkspaceAuthzCacheService {

    private static final Logger log = LoggerFactory.getLogger(WorkspaceAuthzCacheService.class);

    private static final String PREFIX = "dbc:authz:ws:";

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final ManageProperties.AuthzCache props;

    public WorkspaceAuthzCacheService(StringRedisTemplate redisTemplate,
                                      ObjectMapper objectMapper,
                                      ManageProperties manageProperties) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.props = manageProperties.getAuthzCache() == null
                ? new ManageProperties.AuthzCache()
                : manageProperties.getAuthzCache();
    }

    public boolean enabled() {
        return props.isEnabled();
    }

    public Optional<AuthzCacheModels.UserAuthzSnapshot> getUser(Long workspaceId, Long userId) {
        if (!enabled() || workspaceId == null || userId == null) {
            return Optional.empty();
        }
        try {
            String raw = redisTemplate.opsForValue().get(userKey(workspaceId, userId));
            if (!StringUtils.hasText(raw)) {
                return Optional.empty();
            }
            touch(userKey(workspaceId, userId), props.getUserTtlSeconds());
            AuthzCacheModels.UserAuthzSnapshot snap =
                    objectMapper.readValue(raw, AuthzCacheModels.UserAuthzSnapshot.class);
            return Optional.ofNullable(snap);
        } catch (Exception e) {
            log.warn("读取用户授权缓存失败 wsId={} userId={}: {}", workspaceId, userId, e.getMessage(), e);
            return Optional.empty();
        }
    }

    public void putUser(Long workspaceId, Long userId, AuthzCacheModels.UserAuthzSnapshot snapshot) {
        if (!enabled() || workspaceId == null || userId == null || snapshot == null) {
            return;
        }
        try {
            long ver = currentVer(workspaceId);
            snapshot.setVer(ver);
            String json = objectMapper.writeValueAsString(snapshot);
            String uk = userKey(workspaceId, userId);
            redisTemplate.opsForValue().set(uk, json, Duration.ofSeconds(props.getUserTtlSeconds()));
            redisTemplate.opsForSet().add(uidsKey(workspaceId), String.valueOf(userId));
            touch(uidsKey(workspaceId), props.getVerTtlSeconds());
        } catch (Exception e) {
            log.warn("写入用户授权缓存失败 wsId={} userId={}: {}", workspaceId, userId, e.getMessage(), e);
        }
    }

    /**
     * @return empty=未缓存整空间资产；present 且 list 空=该连接无资产
     */
    public Optional<List<AuthzCacheModels.AssetEntry>> getAssetsForConnection(Long workspaceId, Long connectionId) {
        if (!enabled() || workspaceId == null || connectionId == null) {
            return Optional.empty();
        }
        try {
            String ak = assetsKey(workspaceId);
            Boolean exists = redisTemplate.hasKey(ak);
            if (!Boolean.TRUE.equals(exists)) {
                return Optional.empty();
            }
            touch(ak, props.getAssetsTtlSeconds());
            String raw = (String) redisTemplate.opsForHash().get(ak, connField(connectionId));
            if (raw == null) {
                return Optional.of(List.of());
            }
            List<AuthzCacheModels.AssetEntry> list = objectMapper.readValue(
                    raw, new TypeReference<List<AuthzCacheModels.AssetEntry>>() {});
            return Optional.of(list == null ? List.of() : list);
        } catch (Exception e) {
            log.warn("读取空间资产缓存失败 wsId={} connId={}: {}", workspaceId, connectionId, e.getMessage(), e);
            return Optional.empty();
        }
    }

    /** 整空间资产是否已在缓存中。 */
    public boolean hasAssetsSnapshot(Long workspaceId) {
        if (!enabled() || workspaceId == null) {
            return false;
        }
        try {
            return Boolean.TRUE.equals(redisTemplate.hasKey(assetsKey(workspaceId)));
        } catch (Exception e) {
            log.warn("检查空间资产缓存失败 wsId={}: {}", workspaceId, e.getMessage(), e);
            return false;
        }
    }

    public void putAssetsSnapshot(Long workspaceId, Map<Long, List<AuthzCacheModels.AssetEntry>> byConnection) {
        if (!enabled() || workspaceId == null) {
            return;
        }
        try {
            String ak = assetsKey(workspaceId);
            redisTemplate.delete(ak);
            Map<String, String> flat = new HashMap<>();
            if (byConnection != null) {
                for (Map.Entry<Long, List<AuthzCacheModels.AssetEntry>> e : byConnection.entrySet()) {
                    if (e.getKey() == null) {
                        continue;
                    }
                    List<AuthzCacheModels.AssetEntry> list = e.getValue() == null ? List.of() : e.getValue();
                    flat.put(connField(e.getKey()), objectMapper.writeValueAsString(list));
                }
            }
            // 空空间也写占位，避免反复打 DB
            if (flat.isEmpty()) {
                flat.put("_empty", "1");
            }
            redisTemplate.opsForHash().putAll(ak, flat);
            touch(ak, props.getAssetsTtlSeconds());
        } catch (Exception e) {
            log.warn("写入空间资产缓存失败 wsId={}: {}", workspaceId, e.getMessage(), e);
        }
    }

    public Set<Long> listCachedAssetConnectionIds(Long workspaceId) {
        if (!enabled() || workspaceId == null || !hasAssetsSnapshot(workspaceId)) {
            return Set.of();
        }
        try {
            Set<Object> fields = redisTemplate.opsForHash().keys(assetsKey(workspaceId));
            if (fields == null || fields.isEmpty()) {
                return Set.of();
            }
            touch(assetsKey(workspaceId), props.getAssetsTtlSeconds());
            Set<Long> ids = new LinkedHashSet<>();
            for (Object f : fields) {
                String s = String.valueOf(f);
                if (s.startsWith("c:")) {
                    try {
                        ids.add(Long.parseLong(s.substring(2)));
                    } catch (NumberFormatException ignored) {
                        // ignore
                    }
                }
            }
            return ids;
        } catch (Exception e) {
            log.warn("列举资产连接缓存失败 wsId={}: {}", workspaceId, e.getMessage(), e);
            return Set.of();
        }
    }

    public void invalidateAssets(Long workspaceId) {
        if (!enabled() || workspaceId == null) {
            return;
        }
        try {
            bumpVer(workspaceId);
            redisTemplate.delete(assetsKey(workspaceId));
        } catch (Exception e) {
            log.warn("失效空间资产缓存失败 wsId={}: {}", workspaceId, e.getMessage(), e);
        }
    }

    public void invalidateUser(Long workspaceId, Long userId) {
        if (!enabled() || workspaceId == null || userId == null) {
            return;
        }
        try {
            bumpVer(workspaceId);
            redisTemplate.delete(userKey(workspaceId, userId));
            redisTemplate.opsForSet().remove(uidsKey(workspaceId), String.valueOf(userId));
        } catch (Exception e) {
            log.warn("失效用户授权缓存失败 wsId={} userId={}: {}", workspaceId, userId, e.getMessage(), e);
        }
    }

    public void invalidateUsers(Long workspaceId, Iterable<Long> userIds) {
        if (userIds == null) {
            return;
        }
        for (Long userId : userIds) {
            invalidateUser(workspaceId, userId);
        }
    }

    public void invalidateWorkspace(Long workspaceId) {
        if (!enabled() || workspaceId == null) {
            return;
        }
        try {
            String uk = uidsKey(workspaceId);
            Set<String> uids = redisTemplate.opsForSet().members(uk);
            List<String> keys = new ArrayList<>();
            keys.add(assetsKey(workspaceId));
            keys.add(verKey(workspaceId));
            keys.add(uk);
            if (uids != null) {
                for (String uid : uids) {
                    keys.add(userKey(workspaceId, Long.parseLong(uid)));
                }
            }
            redisTemplate.delete(keys);
        } catch (Exception e) {
            log.warn("失效整空间授权缓存失败 wsId={}: {}", workspaceId, e.getMessage(), e);
        }
    }

    private long bumpVer(Long workspaceId) {
        try {
            Long v = redisTemplate.opsForValue().increment(verKey(workspaceId));
            touch(verKey(workspaceId), props.getVerTtlSeconds());
            return v == null ? 0L : v;
        } catch (Exception e) {
            log.warn("递增授权版本失败 wsId={}: {}", workspaceId, e.getMessage(), e);
            return 0L;
        }
    }

    private long currentVer(Long workspaceId) {
        try {
            String v = redisTemplate.opsForValue().get(verKey(workspaceId));
            if (!StringUtils.hasText(v)) {
                return 0L;
            }
            return Long.parseLong(v);
        } catch (Exception e) {
            return 0L;
        }
    }

    private void touch(String key, long ttlSeconds) {
        if (ttlSeconds <= 0) {
            return;
        }
        try {
            redisTemplate.expire(key, ttlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.debug("续期缓存 TTL 失败 key={}: {}", key, e.getMessage());
        }
    }

    private static String assetsKey(Long wsId) {
        return PREFIX + wsId + ":assets";
    }

    private static String userKey(Long wsId, Long userId) {
        return PREFIX + wsId + ":u:" + userId;
    }

    private static String uidsKey(Long wsId) {
        return PREFIX + wsId + ":uids";
    }

    private static String verKey(Long wsId) {
        return PREFIX + wsId + ":ver";
    }

    private static String connField(Long connectionId) {
        return "c:" + connectionId;
    }
}
