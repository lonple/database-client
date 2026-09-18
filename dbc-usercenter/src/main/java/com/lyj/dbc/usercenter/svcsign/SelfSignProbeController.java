package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.Map;

/**
 * 超管触发：HTTP 代签后调用 /inner/ping 自测。
 */
@RestController
@RequestMapping("/apps/self")
public class SelfSignProbeController {

    private final OutboundRequestSigner signer;
    private final CenterSignClient centerSignClient;
    private final RestTemplate restTemplate;

    public SelfSignProbeController(OutboundRequestSigner signer, CenterSignClient centerSignClient,
                                   RestTemplateBuilder builder) {
        this.signer = signer;
        this.centerSignClient = centerSignClient;
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofSeconds(3))
                .setReadTimeout(Duration.ofSeconds(10))
                .build();
    }

    @PostMapping("/probe-inner-ping")
    public ApiResponse<Map<String, Object>> probe() {
        if (!SecurityUtils.requireUser().hasSuperAdmin()) {
            throw BizException.forbidden("仅超级管理员可操作");
        }
        String path = "/inner/ping";
        Map<String, String> signHeaders = signer.signHeaders("GET", path, null, new byte[0]);
        HttpHeaders headers = new HttpHeaders();
        signHeaders.forEach(headers::add);
        ResponseEntity<String> resp = restTemplate.exchange(
                "http://127.0.0.1:8004" + path,
                HttpMethod.GET,
                new HttpEntity<>(headers),
                String.class);
        return ApiResponse.ok(Map.of(
                "status", resp.getStatusCode().value(),
                "kid", centerSignClient.kid() == null ? "" : centerSignClient.kid(),
                "instanceId", centerSignClient.instanceId(),
                "body", resp.getBody() == null ? "" : resp.getBody()
        ));
    }
}
