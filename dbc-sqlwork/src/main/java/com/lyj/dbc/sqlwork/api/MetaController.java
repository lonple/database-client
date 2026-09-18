package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import com.lyj.dbc.sqlwork.api.vo.AuthzEvaluateResult;
import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.MetaTreeVO;
import com.lyj.dbc.sqlwork.api.vo.TablePageVO;
import com.lyj.dbc.sqlwork.client.ManageClient;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.runtime.meta.MetaCatalogService;
import com.lyj.dbc.sqlwork.runtime.meta.MetaVisibilityPlanner;
import com.lyj.dbc.sqlwork.runtime.meta.MetaVisibilityPlanner.NamePlan;
import com.lyj.dbc.sqlwork.runtime.meta.MetaVisibilityPlanner.TablePlan;
import com.lyj.dbc.sqlwork.security.LoginUser;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 工作台元数据 API：按 objectFilter 规划查询，表级白名单下推 IN，避免大资产全量扫描后过滤。
 */
@RestController
@RequestMapping("/meta")
public class MetaController {

    private final ManageClient manageClient;
    private final MetaCatalogService metaCatalogService;

    public MetaController(ManageClient manageClient, MetaCatalogService metaCatalogService) {
        this.manageClient = manageClient;
        this.metaCatalogService = metaCatalogService;
    }

    @GetMapping("/databases")
    public ApiResponse<List<String>> databases(@RequestParam Long workspaceId,
                                               @RequestParam Long connectionId) {
        AuthzContext ctx = authorize(workspaceId, connectionId);
        NamePlan plan = MetaVisibilityPlanner.planDatabases(ctx.authz());
        if (plan.skipCatalog()) {
            return ApiResponse.ok(plan.names() == null ? List.of() : plan.names());
        }
        List<String> all = metaCatalogService.listDatabases(ctx.material());
        if (plan.names() != null) {
            return ApiResponse.ok(MetaVisibilityPlanner.intersectPreserveOrder(all, plan.names()));
        }
        return ApiResponse.ok(all);
    }

    @GetMapping("/schemas")
    public ApiResponse<List<String>> schemas(@RequestParam Long workspaceId,
                                             @RequestParam Long connectionId,
                                             @RequestParam(required = false) String database) {
        AuthzContext ctx = authorize(workspaceId, connectionId);
        NamePlan plan = MetaVisibilityPlanner.planSchemas(ctx.authz(), database);
        if (plan.skipCatalog()) {
            return ApiResponse.ok(plan.names() == null ? List.of() : plan.names());
        }
        List<String> all = metaCatalogService.listSchemas(ctx.material(), database);
        if (plan.names() != null) {
            return ApiResponse.ok(MetaVisibilityPlanner.intersectPreserveOrder(all, plan.names()));
        }
        return ApiResponse.ok(all);
    }

    @GetMapping("/tables")
    public ApiResponse<TablePageVO> tables(@RequestParam Long workspaceId,
                                           @RequestParam Long connectionId,
                                           @RequestParam(required = false) String database,
                                           @RequestParam(required = false) String schema,
                                           @RequestParam(required = false) String keyword,
                                           @RequestParam(defaultValue = "1") int page,
                                           @RequestParam(defaultValue = "50") int size) {
        AuthzContext ctx = authorize(workspaceId, connectionId);
        TablePlan plan = MetaVisibilityPlanner.planTables(ctx.authz(), database, schema);
        return ApiResponse.ok(switch (plan.mode()) {
            case EMPTY -> emptyPage(page, size);
            case NAME_ALLOWLIST -> metaCatalogService.listTables(
                    ctx.material(), database, schema, keyword, plan.nameAllowlist(), page, size);
            case CATALOG_PAGE -> metaCatalogService.listTables(
                    ctx.material(), database, schema, keyword, page, size);
        });
    }

    @GetMapping("/tree")
    public ApiResponse<MetaTreeVO> tree(@RequestParam Long workspaceId,
                                        @RequestParam Long connectionId,
                                        @RequestParam(defaultValue = "100") int tablesPerSchema) {
        AuthzContext ctx = authorize(workspaceId, connectionId);
        int limit = Math.max(tablesPerSchema, 1);

        NamePlan dbPlan = MetaVisibilityPlanner.planDatabases(ctx.authz());
        List<String> databases;
        if (dbPlan.skipCatalog()) {
            databases = dbPlan.names() == null ? List.of() : dbPlan.names();
        } else {
            List<String> all = metaCatalogService.listDatabases(ctx.material());
            databases = dbPlan.names() == null
                    ? all
                    : MetaVisibilityPlanner.intersectPreserveOrder(all, dbPlan.names());
        }

        List<MetaTreeVO.DatabaseNode> dbNodes = new ArrayList<>();
        for (String db : databases) {
            NamePlan schemaPlan = MetaVisibilityPlanner.planSchemas(ctx.authz(), db);
            List<String> schemas;
            if (schemaPlan.skipCatalog()) {
                schemas = schemaPlan.names() == null ? List.of() : schemaPlan.names();
            } else {
                List<String> all = metaCatalogService.listSchemas(ctx.material(), db);
                schemas = schemaPlan.names() == null
                        ? all
                        : MetaVisibilityPlanner.intersectPreserveOrder(all, schemaPlan.names());
            }
            List<MetaTreeVO.SchemaNode> schemaNodes = new ArrayList<>();
            for (String schema : schemas) {
                TablePlan tablePlan = MetaVisibilityPlanner.planTables(ctx.authz(), db, schema);
                TablePageVO tables = switch (tablePlan.mode()) {
                    case EMPTY -> emptyPage(1, limit);
                    case NAME_ALLOWLIST -> metaCatalogService.listTables(
                            ctx.material(), db, schema, null, tablePlan.nameAllowlist(), 1, limit);
                    case CATALOG_PAGE -> metaCatalogService.listTables(
                            ctx.material(), db, schema, null, 1, limit);
                };
                List<MetaTreeVO.TableNode> tableNodes = tables.getItems().stream()
                        .map(t -> new MetaTreeVO.TableNode(t.getName(), t.getObjectType()))
                        .toList();
                schemaNodes.add(new MetaTreeVO.SchemaNode(schema, new ArrayList<>(tableNodes)));
            }
            dbNodes.add(new MetaTreeVO.DatabaseNode(db, schemaNodes));
        }
        return ApiResponse.ok(MetaTreeVO.builder().databases(dbNodes).build());
    }

    private AuthzContext authorize(Long workspaceId, Long connectionId) {
        LoginUser user = SecurityUtils.requireUser();
        String authHeader = SecurityUtils.requireAuthorizationHeader();
        AuthzEvaluateRequest req = new AuthzEvaluateRequest(
                user.getUserId(), workspaceId, connectionId, null, Collections.emptyList(), "WORKBENCH",
                null, null);
        AuthzEvaluateResult authz = manageClient.evaluate(req, authHeader);
        if (!authz.isAllowed() || !authz.isConnectionAllowed()) {
            throw BizException.forbidden(authz.getMessage() == null ? "无元数据访问权限" : authz.getMessage());
        }
        ConnectionMaterial material = manageClient.getMaterial(connectionId, authHeader);
        return new AuthzContext(material, authz);
    }

    private static TablePageVO emptyPage(int page, int size) {
        return TablePageVO.builder()
                .items(List.of())
                .total(0)
                .page(Math.max(page, 1))
                .size(Math.max(size, 1))
                .build();
    }

    private record AuthzContext(ConnectionMaterial material, AuthzEvaluateResult authz) {
    }
}
