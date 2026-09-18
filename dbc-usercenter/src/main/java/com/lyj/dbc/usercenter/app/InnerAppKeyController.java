package com.lyj.dbc.usercenter.app;

import com.lyj.dbc.usercenter.app.dto.AppKeyApplyRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyHeartbeatRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyRevokeRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeyRotateRequest;
import com.lyj.dbc.usercenter.app.dto.AppKeySignRequest;
import com.lyj.dbc.usercenter.app.vo.AppKeySignResultVO;
import com.lyj.dbc.usercenter.app.vo.AppKeyVO;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.mtls.MtlsClientContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 应用密钥 API：须经 mTLS 端口访问，身份取自客户端证书 CN。
 */
@RestController
@RequestMapping("/inner/apps/keys")
public class InnerAppKeyController {

    private final AppKeyService appKeyService;

    public InnerAppKeyController(AppKeyService appKeyService) {
        this.appKeyService = appKeyService;
    }

    @PostMapping("/apply")
    public ApiResponse<AppKeyVO> apply(@Valid @RequestBody AppKeyApplyRequest request) {
        return ApiResponse.ok(appKeyService.apply(requireMtlsClientId(), request));
    }

    @PostMapping("/sign")
    public ApiResponse<AppKeySignResultVO> sign(@Valid @RequestBody AppKeySignRequest request) {
        return ApiResponse.ok(appKeyService.sign(requireMtlsClientId(), request));
    }

    @PostMapping("/heartbeat")
    public ApiResponse<Void> heartbeat(@Valid @RequestBody AppKeyHeartbeatRequest request) {
        appKeyService.heartbeat(requireMtlsClientId(), request);
        return ApiResponse.ok(null);
    }

    @PostMapping("/rotate")
    public ApiResponse<AppKeyVO> rotate(@Valid @RequestBody AppKeyRotateRequest request) {
        return ApiResponse.ok(appKeyService.rotate(requireMtlsClientId(), request));
    }

    @PostMapping("/revoke")
    public ApiResponse<Void> revoke(@Valid @RequestBody AppKeyRevokeRequest request) {
        appKeyService.revokeByClient(requireMtlsClientId(), request);
        return ApiResponse.ok(null);
    }

    @GetMapping("/public")
    public ApiResponse<List<AppKeyVO>> publicKeys() {
        requireMtlsClientId();
        return ApiResponse.ok(appKeyService.listAlivePublicKeys());
    }

    private String requireMtlsClientId() {
        String clientId = MtlsClientContext.getClientId();
        if (clientId == null || clientId.isBlank()) {
            throw BizException.forbidden("缺少 mTLS 客户端身份");
        }
        return clientId;
    }
}
