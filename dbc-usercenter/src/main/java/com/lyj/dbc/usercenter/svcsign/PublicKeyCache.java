package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.app.AppKeyService;
import com.lyj.dbc.usercenter.app.entity.AppKeyEntity;
import com.lyj.dbc.usercenter.app.vo.AppKeyVO;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.security.PublicKey;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 缓存可用于验签的公钥。
 */
@Component
@Order(3)
public class PublicKeyCache implements ApplicationRunner {

    private final AppKeyService appKeyService;
    private final Map<String, PublicKey> cache = new ConcurrentHashMap<>();

    public PublicKeyCache(AppKeyService appKeyService) {
        this.appKeyService = appKeyService;
    }

    @Override
    public void run(ApplicationArguments args) {
        refresh();
    }

    @Scheduled(fixedDelayString = "${dbc.svc-sign.public-key-refresh-ms:30000}")
    public void refresh() {
        List<AppKeyVO> keys = appKeyService.listAlivePublicKeys();
        Map<String, PublicKey> next = new ConcurrentHashMap<>();
        for (AppKeyVO vo : keys) {
            try {
                next.put(cacheKey(vo.getClientId(), vo.getKid()),
                        EcdsaSignSupport.parsePublicPem(vo.getPublicKeyPem()));
            } catch (Exception ignored) {
                // skip invalid pem
            }
        }
        cache.clear();
        cache.putAll(next);
    }

    public PublicKey get(String clientId, String kid) {
        PublicKey cached = cache.get(cacheKey(clientId, kid));
        if (cached != null) {
            return cached;
        }
        AppKeyEntity entity = appKeyService.findAliveKey(clientId, kid);
        if (entity == null) {
            return null;
        }
        PublicKey key = EcdsaSignSupport.parsePublicPem(entity.getPublicKeyPem());
        cache.put(cacheKey(clientId, kid), key);
        return key;
    }

    private static String cacheKey(String clientId, String kid) {
        return clientId + "|" + kid;
    }
}
