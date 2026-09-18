package com.lyj.dbc.manage.asset.connection;

import com.lyj.dbc.manage.asset.connection.dto.ConnectionCreateRequest;
import com.lyj.dbc.manage.asset.connection.dto.ConnectionPingRequest;
import com.lyj.dbc.manage.asset.connection.dto.ConnectionUpdateRequest;
import com.lyj.dbc.manage.asset.connection.vo.ConnectionPingResultVO;
import com.lyj.dbc.manage.asset.connection.vo.ConnectionVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.security.RequirePermission;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 连接管理接口。
 */
@Validated
@RestController
@RequestMapping("/connections")
public class ConnectionController {

    private final ConnectionService connectionService;

    public ConnectionController(ConnectionService connectionService) {
        this.connectionService = connectionService;
    }

    @GetMapping
    @RequirePermission("manage.connection.view")
    public ApiResponse<List<ConnectionVO>> list() {
        return ApiResponse.ok(connectionService.list());
    }

    @GetMapping("/{id}")
    @RequirePermission("manage.connection.view")
    public ApiResponse<ConnectionVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(connectionService.getById(id));
    }

    /**
     * 创建/编辑表单连接测试（经 sqlwork 探活，manage 不直连目标库）。
     */
    @PostMapping("/ping")
    @RequirePermission("manage.connection.operate")
    public ApiResponse<ConnectionPingResultVO> ping(@Valid @RequestBody ConnectionPingRequest request) {
        return ApiResponse.ok(connectionService.ping(request));
    }

    @PostMapping
    @RequirePermission("manage.connection.operate")
    public ApiResponse<ConnectionVO> create(@Valid @RequestBody ConnectionCreateRequest request) {
        return ApiResponse.ok(connectionService.create(request));
    }

    @PutMapping("/{id}")
    @RequirePermission("manage.connection.operate")
    public ApiResponse<ConnectionVO> update(@PathVariable @Min(1) Long id,
                                            @Valid @RequestBody ConnectionUpdateRequest request) {
        return ApiResponse.ok(connectionService.update(id, request));
    }

    @DeleteMapping("/{id}")
    @RequirePermission("manage.connection.operate")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        connectionService.delete(id);
        return ApiResponse.ok(null);
    }
}
