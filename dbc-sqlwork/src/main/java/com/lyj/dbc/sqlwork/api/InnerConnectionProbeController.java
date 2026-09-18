package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.ConnectionPingResult;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.runtime.pool.ConnectionProbeService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * manage 转发的草稿/材料探活（JWT 由 manage 转发；不经连接池缓存）。
 */
@RestController
@RequestMapping("/inner/connections")
public class InnerConnectionProbeController {

    private final ConnectionProbeService connectionProbeService;

    public InnerConnectionProbeController(ConnectionProbeService connectionProbeService) {
        this.connectionProbeService = connectionProbeService;
    }

    @PostMapping("/ping")
    public ApiResponse<ConnectionPingResult> ping(@Valid @RequestBody ConnectionMaterial material) {
        return ApiResponse.ok(connectionProbeService.ping(material));
    }
}
