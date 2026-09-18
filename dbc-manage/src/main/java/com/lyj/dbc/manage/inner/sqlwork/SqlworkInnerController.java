package com.lyj.dbc.manage.inner.sqlwork;

import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.inner.sqlwork.dto.AuthzEvaluateRequest;
import com.lyj.dbc.manage.inner.sqlwork.vo.AuthzEvaluateResult;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionMaterialVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionSummaryVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.MyWorkspaceAuthzVO;
import com.lyj.dbc.manage.inner.sqlwork.vo.WorkspaceSummaryVO;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 供 dbc-sqlwork 调用的内部接口。
 */
@Validated
@RestController
@RequestMapping("/inner/sqlwork")
public class SqlworkInnerController {

    private final SqlworkInnerService sqlworkInnerService;
    private final SqlworkAuthzService sqlworkAuthzService;

    public SqlworkInnerController(SqlworkInnerService sqlworkInnerService,
                                  SqlworkAuthzService sqlworkAuthzService) {
        this.sqlworkInnerService = sqlworkInnerService;
        this.sqlworkAuthzService = sqlworkAuthzService;
    }

    @GetMapping("/workspaces/mine")
    public ApiResponse<List<WorkspaceSummaryVO>> myWorkspaces() {
        return ApiResponse.ok(sqlworkInnerService.listMyWorkspaces());
    }

    @GetMapping("/workspaces/{workspaceId}/connections")
    public ApiResponse<List<ConnectionSummaryVO>> workspaceConnections(
            @PathVariable @Min(1) Long workspaceId) {
        return ApiResponse.ok(sqlworkInnerService.listWorkspaceConnections(workspaceId));
    }

    @GetMapping("/workspaces/{workspaceId}/my-authz")
    public ApiResponse<MyWorkspaceAuthzVO> myAuthz(@PathVariable @Min(1) Long workspaceId) {
        return ApiResponse.ok(sqlworkInnerService.getMyAuthz(workspaceId));
    }

    @GetMapping("/connections/{connectionId}/material")
    public ApiResponse<ConnectionMaterialVO> connectionMaterial(
            @PathVariable @Min(1) Long connectionId) {
        return ApiResponse.ok(sqlworkInnerService.getConnectionMaterial(connectionId));
    }

    @PostMapping("/authz/evaluate")
    public ApiResponse<AuthzEvaluateResult> evaluate(@RequestBody AuthzEvaluateRequest request) {
        return ApiResponse.ok(sqlworkAuthzService.evaluate(request));
    }
}
