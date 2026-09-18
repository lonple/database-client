package com.lyj.dbc.usercenter.app;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.usercenter.app.dto.AppCreateRequest;
import com.lyj.dbc.usercenter.app.entity.AppEntity;
import com.lyj.dbc.usercenter.app.mapper.AppMapper;
import com.lyj.dbc.usercenter.app.vo.AppVO;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.mtls.MtlsCertificateService;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.file.Files;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 应用（微服务）管理；客户端身份凭证为 mTLS 证书。
 */
@Service
public class AppService {

    private final AppMapper appMapper;
    private final MtlsCertificateService mtlsCertificateService;

    public AppService(AppMapper appMapper, MtlsCertificateService mtlsCertificateService) {
        this.appMapper = appMapper;
        this.mtlsCertificateService = mtlsCertificateService;
    }

    /** 启动时为所有启用应用签发缺失的客户端证书 */
    public void ensureAllClientCerts() {
        mtlsCertificateService.ensureCaAndServer();
        List<AppEntity> apps = appMapper.selectList(new LambdaQueryWrapper<AppEntity>()
                .eq(AppEntity::getStatus, 1));
        for (AppEntity app : apps) {
            mtlsCertificateService.ensureClientCert(app.getClientId());
        }
    }

    public List<AppVO> listAll() {
        assertSuperAdmin();
        return appMapper.selectList(new LambdaQueryWrapper<AppEntity>().orderByAsc(AppEntity::getId))
                .stream().map(this::toVo).toList();
    }

    @Transactional
    public AppVO create(AppCreateRequest request) {
        assertSuperAdmin();
        String clientId = request.getClientId().trim();
        Long exists = appMapper.selectCount(new LambdaQueryWrapper<AppEntity>()
                .eq(AppEntity::getClientId, clientId));
        if (exists != null && exists > 0) {
            throw BizException.conflict("clientId 已存在");
        }
        AppEntity app = new AppEntity();
        app.setClientId(clientId);
        app.setAppName(request.getAppName().trim());
        app.setBuiltin(0);
        app.setStatus(1);
        app.setCreatedAt(OffsetDateTime.now());
        app.setUpdatedAt(OffsetDateTime.now());
        appMapper.insert(app);
        mtlsCertificateService.ensureClientCert(clientId);
        return toVo(appMapper.selectById(app.getId()));
    }

    @Transactional
    public AppVO updateStatus(Long id, int status) {
        assertSuperAdmin();
        AppEntity app = requireApp(id);
        if (app.getBuiltin() != null && app.getBuiltin() == 1 && status == 0) {
            throw BizException.badRequest("内置应用不可停用");
        }
        app.setStatus(status);
        app.setUpdatedAt(OffsetDateTime.now());
        appMapper.updateById(app);
        return toVo(app);
    }

    /** 重新签发客户端证书 */
    public void reissueClientCert(Long id) {
        assertSuperAdmin();
        AppEntity app = requireApp(id);
        mtlsCertificateService.reissueClientCert(app.getClientId());
    }

    public AppEntity requireById(Long id) {
        return requireApp(id);
    }

    public AppEntity requireByClientId(String clientId) {
        AppEntity app = appMapper.selectOne(new LambdaQueryWrapper<AppEntity>()
                .eq(AppEntity::getClientId, clientId));
        if (app == null) {
            throw BizException.unauthorized("未知应用");
        }
        if (app.getStatus() == null || app.getStatus() != 1) {
            throw BizException.unauthorized("应用已停用");
        }
        return app;
    }

    private AppEntity requireApp(Long id) {
        AppEntity app = appMapper.selectById(id);
        if (app == null) {
            throw BizException.notFound("应用不存在");
        }
        return app;
    }

    private AppVO toVo(AppEntity app) {
        AppVO vo = new AppVO();
        vo.setId(app.getId());
        vo.setClientId(app.getClientId());
        vo.setAppName(app.getAppName());
        vo.setBuiltin(app.getBuiltin());
        vo.setStatus(app.getStatus());
        vo.setHasClientCert(Files.exists(mtlsCertificateService.clientP12Path(app.getClientId())));
        vo.setCreatedAt(app.getCreatedAt());
        vo.setUpdatedAt(app.getUpdatedAt());
        return vo;
    }

    private void assertSuperAdmin() {
        LoginUser user = SecurityUtils.requireUser();
        if (!user.hasSuperAdmin()) {
            throw BizException.forbidden("仅超级管理员可操作应用管理");
        }
    }
}
