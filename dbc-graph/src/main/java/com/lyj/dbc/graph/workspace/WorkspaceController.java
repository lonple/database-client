package com.lyj.dbc.graph.workspace;

import com.lyj.dbc.graph.common.api.ApiResponse;
import com.lyj.dbc.graph.workspace.dto.WorkspaceTreeNode;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/workspace")
public class WorkspaceController {
    private final WorkspaceService workspaceService;

    public WorkspaceController(WorkspaceService workspaceService) {
        this.workspaceService = workspaceService;
    }

    @GetMapping("/tree")
    public ApiResponse<List<WorkspaceTreeNode>> tree() {
        return ApiResponse.ok(workspaceService.tree());
    }
}
