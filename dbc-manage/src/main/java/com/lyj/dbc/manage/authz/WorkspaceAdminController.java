package com.lyj.dbc.manage.authz;

import com.lyj.dbc.manage.authz.dto.WorkspaceAdminRequests;
import com.lyj.dbc.manage.authz.vo.WorkspaceDetailVO;
import com.lyj.dbc.manage.authz.vo.WorkspaceListItemVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.inner.sqlwork.vo.WorkspaceSummaryVO;
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
 * 工作空间管理接口。
 */
@Validated
@RestController
@RequestMapping("/workspaces")
public class WorkspaceAdminController {

    private final WorkspaceAdminService workspaceAdminService;

    public WorkspaceAdminController(WorkspaceAdminService workspaceAdminService) {
        this.workspaceAdminService = workspaceAdminService;
    }

    @RequirePermission("auth.workspace.operate")
    @PostMapping
    public ApiResponse<WorkspaceSummaryVO> create(
            @Valid @RequestBody WorkspaceAdminRequests.CreateWorkspaceRequest request) {
        return ApiResponse.ok(workspaceAdminService.create(request));
    }

    @GetMapping("/personal")
    public ApiResponse<WorkspaceSummaryVO> getPersonal() {
        return ApiResponse.ok(workspaceAdminService.getPersonal());
    }

    @PostMapping("/personal")
    public ApiResponse<WorkspaceSummaryVO> ensurePersonal(
            @RequestBody(required = false) WorkspaceAdminRequests.CreateWorkspaceRequest request) {
        return ApiResponse.ok(workspaceAdminService.ensurePersonal(request));
    }

    @RequirePermission("auth.workspace.view")
    @GetMapping("/mine")
    public ApiResponse<List<WorkspaceListItemVO>> mine() {
        return ApiResponse.ok(workspaceAdminService.listMineDetailed());
    }

    @GetMapping("/{id}")
    public ApiResponse<WorkspaceDetailVO> detail(@PathVariable @Min(1) Long id) {
        return ApiResponse.ok(workspaceAdminService.getDetail(id));
    }

    @PostMapping("/{id}/members")
    public ApiResponse<Void> addMembers(@PathVariable @Min(1) Long id,
                                        @Valid @RequestBody WorkspaceAdminRequests.AddMembersRequest request) {
        workspaceAdminService.addMembers(id, request);
        return ApiResponse.ok(null);
    }

    @PutMapping("/{id}/members/{userId}/role")
    public ApiResponse<Void> setMemberRole(@PathVariable @Min(1) Long id,
                                           @PathVariable @Min(1) Long userId,
                                           @Valid @RequestBody WorkspaceAdminRequests.SetMemberRoleRequest request) {
        workspaceAdminService.setMemberRole(id, userId, request);
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{id}/members/{userId}")
    public ApiResponse<Void> removeMember(@PathVariable @Min(1) Long id,
                                          @PathVariable @Min(1) Long userId) {
        workspaceAdminService.removeMember(id, userId);
        return ApiResponse.ok(null);
    }

    @PostMapping("/{id}/assets")
    public ApiResponse<Void> addAsset(@PathVariable @Min(1) Long id,
                                      @Valid @RequestBody WorkspaceAdminRequests.AddAssetRequest request) {
        workspaceAdminService.addAsset(id, request);
        return ApiResponse.ok(null);
    }

    @PutMapping("/{id}/assets/{assetId}")
    public ApiResponse<Void> updateAsset(@PathVariable @Min(1) Long id,
                                         @PathVariable @Min(1) Long assetId,
                                         @Valid @RequestBody WorkspaceAdminRequests.UpdateAssetRequest request) {
        workspaceAdminService.updateAsset(id, assetId, request);
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{id}/assets/{assetId}")
    public ApiResponse<Void> removeAsset(@PathVariable @Min(1) Long id,
                                         @PathVariable @Min(1) Long assetId) {
        workspaceAdminService.removeAsset(id, assetId);
        return ApiResponse.ok(null);
    }

    @PostMapping("/{id}/member-grants")
    public ApiResponse<Void> addMemberGrant(@PathVariable @Min(1) Long id,
                                            @Valid @RequestBody WorkspaceAdminRequests.AddMemberGrantRequest request) {
        workspaceAdminService.addMemberGrant(id, request);
        return ApiResponse.ok(null);
    }

    @PostMapping("/{id}/member-grants/batch")
    public ApiResponse<Void> batchMemberGrants(@PathVariable @Min(1) Long id,
                                               @Valid @RequestBody WorkspaceAdminRequests.BatchMemberGrantRequest request) {
        workspaceAdminService.batchMemberGrants(id, request);
        return ApiResponse.ok(null);
    }

    @PutMapping("/{id}/member-grants/{grantId}")
    public ApiResponse<Void> updateMemberGrant(@PathVariable @Min(1) Long id,
                                               @PathVariable @Min(1) Long grantId,
                                               @Valid @RequestBody WorkspaceAdminRequests.UpdateMemberGrantRequest request) {
        workspaceAdminService.updateMemberGrant(id, grantId, request);
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{id}/member-grants/{grantId}")
    public ApiResponse<Void> removeMemberGrant(@PathVariable @Min(1) Long id,
                                               @PathVariable @Min(1) Long grantId) {
        workspaceAdminService.removeMemberGrant(id, grantId);
        return ApiResponse.ok(null);
    }
}
