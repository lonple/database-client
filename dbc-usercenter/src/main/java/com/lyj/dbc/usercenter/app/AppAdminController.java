package com.lyj.dbc.usercenter.app;

import com.lyj.dbc.usercenter.app.dto.AppCreateRequest;
import com.lyj.dbc.usercenter.app.vo.AppKeyVO;
import com.lyj.dbc.usercenter.app.vo.AppVO;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.svcsign.CenterSignClient;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 应用管理（超管）。
 */
@RestController
@RequestMapping("/apps")
public class AppAdminController {

    private final AppService appService;
    private final AppKeyService appKeyService;
    private final CenterSignClient centerSignClient;

    public AppAdminController(AppService appService, AppKeyService appKeyService,
                              CenterSignClient centerSignClient) {
        this.appService = appService;
        this.appKeyService = appKeyService;
        this.centerSignClient = centerSignClient;
    }

    @GetMapping
    public ApiResponse<List<AppVO>> list() {
        return ApiResponse.ok(appService.listAll());
    }

    @PostMapping
    public ApiResponse<AppVO> create(@Valid @RequestBody AppCreateRequest request) {
        return ApiResponse.ok(appService.create(request));
    }

    @PutMapping("/{id}/status")
    public ApiResponse<AppVO> status(@PathVariable Long id, @RequestParam int status) {
        return ApiResponse.ok(appService.updateStatus(id, status));
    }

    @PostMapping("/{id}/reissue-cert")
    public ApiResponse<Void> reissueCert(@PathVariable Long id) {
        appService.reissueClientCert(id);
        return ApiResponse.ok(null);
    }

    @GetMapping("/{id}/keys")
    public ApiResponse<List<AppKeyVO>> keys(@PathVariable Long id) {
        return ApiResponse.ok(appKeyService.listByAppId(id));
    }

    @PostMapping("/{id}/keys/{kid}/revoke")
    public ApiResponse<Void> revoke(@PathVariable Long id, @PathVariable String kid) {
        appKeyService.revokeByAdmin(id, kid);
        return ApiResponse.ok(null);
    }

    /** 本服务实例经 HTTP 向中心轮换签名密钥 */
    @PostMapping("/self/rotate-signing-key")
    public ApiResponse<AppKeyVO> rotateSelf() {
        assertSuperAdmin();
        return ApiResponse.ok(centerSignClient.rotate());
    }

    @GetMapping("/self/signing-key")
    public ApiResponse<Map<String, String>> selfKey() {
        assertSuperAdmin();
        return ApiResponse.ok(Map.of(
                "clientId", centerSignClient.clientId(),
                "instanceId", centerSignClient.instanceId(),
                "kid", centerSignClient.kid() == null ? "" : centerSignClient.kid()
        ));
    }

    private void assertSuperAdmin() {
        if (!SecurityUtils.requireUser().hasSuperAdmin()) {
            throw BizException.forbidden("仅超级管理员可操作应用管理");
        }
    }
}
