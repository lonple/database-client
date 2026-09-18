package com.lyj.dbc.usercenter.app;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.usercenter.app.dto.AppKeyApplyRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyHeartbeatRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyRevokeRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyRotateRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeySignRequest;
import com.lyj.dbc.usercenter.app.entity.AppEntity;
import com.lyj.dbc.usercenter.app.entity.AppKeyEntity;
import com.lyj.dbc.usercenter.app.mapper.AppKeyMapper;
import com.lyj.dbc.usercenter.app.vo.AppKeySignResultVO;
import com.lyj.dbc.usercenter.app.vo.AppKeyVO;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.config.SvcSignProperties;
import com.lyj.dbc.usercenter.secrets.KekCryptoService;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.svcsign.EcdsaSignSupport;
import com.lyj.dbc.usercenter.svcsign.SignCanonical;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.KeyPair;
import java.security.PrivateKey;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 应用密钥：中心生成保管私钥、代签、心跳、轮换、公钥查询。
 */
@Service
public class AppKeyService {

    private final AppKeyMapper appKeyMapper;
    private final AppService appService;
    private final SvcSignProperties svcSignProperties;
    private final KekCryptoService kekCryptoService;

    public AppKeyService(AppKeyMapper appKeyMapper, AppService appService,
                         SvcSignProperties svcSignProperties, KekCryptoService kekCryptoService) {
        this.appKeyMapper = appKeyMapper;
        this.appService = appService;
        this.svcSignProperties = svcSignProperties;
        this.kekCryptoService = kekCryptoService;
    }

    /**
     * 为实例申请密钥：已有存活 kid 则复用并续心跳，否则新建。
     */
    @Transactional
    public AppKeyVO apply(String clientId, AppKeyApplyRequest request) {
        appService.requireByClientId(clientId);
        return applyInternal(clientId, request.getInstanceId().trim());
    }

    @Transactional
    public AppKeyVO applyInternal(String clientId, String instanceId) {
        appService.requireByClientId(clientId);
        OffsetDateTime now = OffsetDateTime.now();
        AppKeyEntity alive = findAliveByInstance(clientId, instanceId, now);
        if (alive != null) {
            alive.setLastSeenAt(now);
            appKeyMapper.updateById(alive);
            return toVo(alive, now);
        }
        return createKeyPair(clientId, instanceId, now);
    }

    @Transactional
    public AppKeyVO rotate(String clientId, AppKeyRotateRequest request) {
        appService.requireByClientId(clientId);
        return rotateInternal(clientId, request.getInstanceId().trim());
    }

    @Transactional
    public AppKeyVO rotateInternal(String clientId, String instanceId) {
        OffsetDateTime now = OffsetDateTime.now();
        AppKeyEntity old = findAliveByInstance(clientId, instanceId, now);
        AppKeyVO created = createKeyPair(clientId, instanceId, now);
        if (old != null) {
            old.setStatus("revoked");
            old.setRevokedAt(now);
            appKeyMapper.updateById(old);
        }
        return created;
    }

    @Transactional
    public AppKeySignResultVO sign(String clientId, AppKeySignRequest request) {
        appService.requireByClientId(clientId);
        OffsetDateTime now = OffsetDateTime.now();
        AppKeyEntity key = findAliveByInstance(clientId, request.getInstanceId().trim(), now);
        if (key == null || key.getPrivateKeyCipher() == null || key.getPrivateKeyCipher().isBlank()) {
            throw BizException.unauthorized("实例无可用签名密钥，请先申请");
        }
        String stringToSign = buildWithBodyHash(
                request.getMethod(), request.getPath(), request.getQuery(),
                request.getTimestamp(), request.getNonce(), request.getBodySha256Hex());

        PrivateKey privateKey = EcdsaSignSupport.parsePrivatePem(
                kekCryptoService.decrypt(key.getPrivateKeyCipher()));
        String signature = EcdsaSignSupport.sign(privateKey, stringToSign);
        key.setLastSeenAt(now);
        appKeyMapper.updateById(key);
        return new AppKeySignResultVO(key.getKid(), signature, request.getTimestamp(), request.getNonce());
    }

    @Transactional
    public void heartbeat(String clientId, AppKeyHeartbeatRequest request) {
        appService.requireByClientId(clientId);
        OffsetDateTime now = OffsetDateTime.now();
        AppKeyEntity key = findAliveByInstance(clientId, request.getInstanceId().trim(), now);
        if (key == null) {
            throw BizException.notFound("实例无存活密钥");
        }
        key.setLastSeenAt(now);
        appKeyMapper.updateById(key);
    }

    @Transactional
    public void revokeByClient(String clientId, AppKeyRevokeRequest request) {
        appService.requireByClientId(clientId);
        revokeInternal(clientId, request.getKid());
    }

    @Transactional
    public void revokeByAdmin(Long appId, String kid) {
        assertSuperAdmin();
        AppEntity app = appService.requireById(appId);
        revokeInternal(app.getClientId(), kid);
    }

    @Transactional
    public void revokeInternal(String clientId, String kid) {
        AppKeyEntity entity = requireKey(clientId, kid);
        entity.setStatus("revoked");
        entity.setRevokedAt(OffsetDateTime.now());
        appKeyMapper.updateById(entity);
    }

    public List<AppKeyVO> listAlivePublicKeys() {
        OffsetDateTime now = OffsetDateTime.now();
        return appKeyMapper.selectList(new LambdaQueryWrapper<AppKeyEntity>()
                        .eq(AppKeyEntity::getStatus, "active")
                        .orderByDesc(AppKeyEntity::getLastSeenAt))
                .stream()
                .filter(k -> isAlive(k, now))
                .map(k -> toVo(k, now))
                .toList();
    }

    public List<AppKeyVO> listByAppId(Long appId) {
        assertSuperAdmin();
        AppEntity app = appService.requireById(appId);
        OffsetDateTime now = OffsetDateTime.now();
        return appKeyMapper.selectList(new LambdaQueryWrapper<AppKeyEntity>()
                        .eq(AppKeyEntity::getClientId, app.getClientId())
                        .orderByDesc(AppKeyEntity::getCreatedAt))
                .stream().map(k -> toVo(k, now)).toList();
    }

    public AppKeyEntity findAliveKey(String clientId, String kid) {
        AppKeyEntity entity = appKeyMapper.selectOne(new LambdaQueryWrapper<AppKeyEntity>()
                .eq(AppKeyEntity::getClientId, clientId)
                .eq(AppKeyEntity::getKid, kid)
                .eq(AppKeyEntity::getStatus, "active"));
        if (entity == null || !isAlive(entity, OffsetDateTime.now())) {
            return null;
        }
        return entity;
    }

    private AppKeyVO createKeyPair(String clientId, String instanceId, OffsetDateTime now) {
        long aliveCount = countAliveKeys(clientId, now);
        if (aliveCount >= svcSignProperties.getMaxActiveKidsPerApp()) {
            throw BizException.badRequest("该应用 active kid 数量已达上限");
        }
        KeyPair pair = EcdsaSignSupport.generateKeyPair();
        String kid = instanceId + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        AppKeyEntity entity = new AppKeyEntity();
        entity.setClientId(clientId);
        entity.setKid(kid);
        entity.setAlgorithm(EcdsaSignSupport.ALG);
        entity.setPublicKeyPem(EcdsaSignSupport.toPemPublic(pair.getPublic()));
        entity.setPrivateKeyCipher(kekCryptoService.encrypt(EcdsaSignSupport.toPemPrivate(pair.getPrivate())));
        entity.setInstanceId(instanceId);
        entity.setStatus("active");
        entity.setCreatedAt(now);
        entity.setLastSeenAt(now);
        appKeyMapper.insert(entity);
        return toVo(entity, now);
    }

    private AppKeyEntity findAliveByInstance(String clientId, String instanceId, OffsetDateTime now) {
        List<AppKeyEntity> list = appKeyMapper.selectList(new LambdaQueryWrapper<AppKeyEntity>()
                .eq(AppKeyEntity::getClientId, clientId)
                .eq(AppKeyEntity::getInstanceId, instanceId)
                .eq(AppKeyEntity::getStatus, "active")
                .orderByDesc(AppKeyEntity::getLastSeenAt));
        return list.stream().filter(k -> isAlive(k, now)).findFirst().orElse(null);
    }

    private static String buildWithBodyHash(String method, String path, String query,
                                            String timestamp, String nonce, String bodySha256Hex) {
        String m = method == null ? "" : method.trim().toUpperCase();
        String p = path == null || path.isEmpty() ? "/" : path;
        String q = SignCanonical.canonicalQuery(query);
        String hash = bodySha256Hex == null ? "" : bodySha256Hex.trim().toLowerCase();
        return m + "\n" + p + "\n" + q + "\n" + timestamp + "\n" + nonce + "\n" + hash;
    }

    private long countAliveKeys(String clientId, OffsetDateTime now) {
        return appKeyMapper.selectList(new LambdaQueryWrapper<AppKeyEntity>()
                        .eq(AppKeyEntity::getClientId, clientId)
                        .eq(AppKeyEntity::getStatus, "active"))
                .stream().filter(k -> isAlive(k, now)).count();
    }

    private boolean isAlive(AppKeyEntity key, OffsetDateTime now) {
        if (key.getLastSeenAt() == null) {
            return false;
        }
        return !key.getLastSeenAt().isBefore(now.minusSeconds(svcSignProperties.getHeartbeatStaleSeconds()));
    }

    private AppKeyEntity requireKey(String clientId, String kid) {
        AppKeyEntity entity = appKeyMapper.selectOne(new LambdaQueryWrapper<AppKeyEntity>()
                .eq(AppKeyEntity::getClientId, clientId)
                .eq(AppKeyEntity::getKid, kid));
        if (entity == null) {
            throw BizException.notFound("公钥不存在");
        }
        return entity;
    }

    private AppKeyVO toVo(AppKeyEntity entity, OffsetDateTime now) {
        AppKeyVO vo = new AppKeyVO();
        vo.setId(entity.getId());
        vo.setClientId(entity.getClientId());
        vo.setKid(entity.getKid());
        vo.setAlgorithm(entity.getAlgorithm());
        vo.setPublicKeyPem(entity.getPublicKeyPem());
        vo.setInstanceId(entity.getInstanceId());
        vo.setStatus(entity.getStatus());
        vo.setAlive("active".equals(entity.getStatus()) && isAlive(entity, now));
        vo.setCreatedAt(entity.getCreatedAt());
        vo.setLastSeenAt(entity.getLastSeenAt());
        vo.setRevokedAt(entity.getRevokedAt());
        return vo;
    }

    private void assertSuperAdmin() {
        LoginUser user = SecurityUtils.requireUser();
        if (!user.hasSuperAdmin()) {
            throw BizException.forbidden("仅超级管理员可操作");
        }
    }
}
