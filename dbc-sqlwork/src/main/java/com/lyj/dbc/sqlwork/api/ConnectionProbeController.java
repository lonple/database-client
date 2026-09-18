package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.ConnectionPingResult;
import com.lyj.dbc.sqlwork.client.ManageClient;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.runtime.pool.ConnectionProbeService;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 目标库连接探活（管理端 / 工作台均可调用；实际 JDBC 仅在本服务执行）。
 */
@RestController
@RequestMapping("/connections")
public class ConnectionProbeController {

    private final ManageClient manageClient;
    private final ConnectionProbeService connectionProbeService;

    public ConnectionProbeController(ManageClient manageClient, ConnectionProbeService connectionProbeService) {
        this.manageClient = manageClient;
        this.connectionProbeService = connectionProbeService;
    }

    /**
     * 已落库连接探活。
     */
    @PostMapping("/{id}/ping")
    public ApiResponse<ConnectionPingResult> pingById(@PathVariable Long id) {
        String auth = SecurityUtils.requireAuthorizationHeader();
        ConnectionMaterial material = manageClient.getMaterial(id, auth);
        return ApiResponse.ok(connectionProbeService.ping(material));
    }
}
