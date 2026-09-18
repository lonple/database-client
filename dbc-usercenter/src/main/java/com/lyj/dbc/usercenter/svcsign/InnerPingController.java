package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 内部探测接口：用于自测服务签名验签。
 */
@RestController
@RequestMapping("/inner")
public class InnerPingController {

    @GetMapping("/ping")
    public ApiResponse<Map<String, String>> ping() {
        return ApiResponse.ok(Map.of("message", "pong"));
    }
}
