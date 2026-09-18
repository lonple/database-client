package com.lyj.dbc.manage.authz.meta;

import com.lyj.dbc.manage.authz.meta.vo.MetaTablePageVO;
import com.lyj.dbc.manage.common.ApiResponse;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 工作空间授权选表元数据门面：前端 → manage → sqlwork /inner/meta/**。
 * <p>
 * 不做成员表过滤；权限由 {@link com.lyj.dbc.manage.authz.WorkspaceAdminService#assertMetaBrowseAccess} 控制。
 */
@Validated
@RestController
@RequestMapping("/workspaces/{workspaceId}/meta")
public class MetaFacadeController {

    private final MetaFacadeService metaFacadeService;

    public MetaFacadeController(MetaFacadeService metaFacadeService) {
        this.metaFacadeService = metaFacadeService;
    }

    @GetMapping("/databases")
    public ApiResponse<List<String>> databases(@PathVariable @Min(1) Long workspaceId,
                                               @RequestParam @NotNull @Min(1) Long connectionId) {
        return ApiResponse.ok(metaFacadeService.listDatabases(workspaceId, connectionId));
    }

    @GetMapping("/schemas")
    public ApiResponse<List<String>> schemas(@PathVariable @Min(1) Long workspaceId,
                                             @RequestParam @NotNull @Min(1) Long connectionId,
                                             @RequestParam(required = false) @Size(max = 128) String database) {
        return ApiResponse.ok(metaFacadeService.listSchemas(workspaceId, connectionId, database));
    }

    @GetMapping("/tables")
    public ApiResponse<MetaTablePageVO> tables(@PathVariable @Min(1) Long workspaceId,
                                               @RequestParam @NotNull @Min(1) Long connectionId,
                                               @RequestParam(required = false) @Size(max = 128) String database,
                                               @RequestParam(required = false) @Size(max = 128) String schema,
                                               @RequestParam(required = false) @Size(max = 128) String keyword,
                                               @RequestParam(defaultValue = "1") @Min(1) int page,
                                               @RequestParam(defaultValue = "50") @Min(1) @Max(200) int size) {
        return ApiResponse.ok(metaFacadeService.listTables(
                workspaceId, connectionId, database, schema, keyword, page, size));
    }
}
