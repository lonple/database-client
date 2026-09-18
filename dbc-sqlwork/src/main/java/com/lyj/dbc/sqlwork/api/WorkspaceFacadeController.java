package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.vo.ConnectionSummaryVO;
import com.lyj.dbc.sqlwork.api.vo.MyWorkspaceAuthzVO;
import com.lyj.dbc.sqlwork.api.vo.WorkspaceSummaryVO;
import com.lyj.dbc.sqlwork.client.ManageClient;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 工作空间 / 可用连接门面（经 manage inner 聚合）。
 */
@RestController
public class WorkspaceFacadeController {

    private final ManageClient manageClient;

    public WorkspaceFacadeController(ManageClient manageClient) {
        this.manageClient = manageClient;
    }

    @GetMapping("/workspaces/mine")
    public ApiResponse<List<WorkspaceSummaryVO>> mine() {
        String auth = SecurityUtils.requireAuthorizationHeader();
        return ApiResponse.ok(manageClient.listMyWorkspaces(auth));
    }

    @GetMapping("/workspaces/{workspaceId}/connections")
    public ApiResponse<List<ConnectionSummaryVO>> connections(@PathVariable Long workspaceId) {
        String auth = SecurityUtils.requireAuthorizationHeader();
        return ApiResponse.ok(manageClient.listWorkspaceConnections(workspaceId, auth));
    }

    @GetMapping("/workspaces/{workspaceId}/my-authz")
    public ApiResponse<MyWorkspaceAuthzVO> myAuthz(@PathVariable Long workspaceId) {
        String auth = SecurityUtils.requireAuthorizationHeader();
        return ApiResponse.ok(manageClient.getMyAuthz(workspaceId, auth));
    }
}
