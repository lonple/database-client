package com.lyj.dbc.sqlwork.api;

import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.TablePageVO;
import com.lyj.dbc.sqlwork.client.ManageClient;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.runtime.meta.MetaCatalogService;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 供 manage 代理的 inner 元数据（JWT 由 manage 转发终端用户令牌；不做成员表过滤）。
 */
@RestController
@RequestMapping("/inner/meta")
public class InnerMetaController {

    private final ManageClient manageClient;
    private final MetaCatalogService metaCatalogService;

    public InnerMetaController(ManageClient manageClient, MetaCatalogService metaCatalogService) {
        this.manageClient = manageClient;
        this.metaCatalogService = metaCatalogService;
    }

    @GetMapping("/databases")
    public ApiResponse<List<String>> databases(@RequestParam Long connectionId) {
        ConnectionMaterial material = loadMaterial(connectionId);
        return ApiResponse.ok(metaCatalogService.listDatabases(material));
    }

    @GetMapping("/schemas")
    public ApiResponse<List<String>> schemas(@RequestParam Long connectionId,
                                             @RequestParam(required = false) String database) {
        ConnectionMaterial material = loadMaterial(connectionId);
        return ApiResponse.ok(metaCatalogService.listSchemas(material, database));
    }

    @GetMapping("/tables")
    public ApiResponse<TablePageVO> tables(@RequestParam Long connectionId,
                                           @RequestParam(required = false) String database,
                                           @RequestParam(required = false) String schema,
                                           @RequestParam(required = false) String keyword,
                                           @RequestParam(defaultValue = "1") int page,
                                           @RequestParam(defaultValue = "50") int size) {
        ConnectionMaterial material = loadMaterial(connectionId);
        return ApiResponse.ok(metaCatalogService.listTables(material, database, schema, keyword, page, size));
    }

    private ConnectionMaterial loadMaterial(Long connectionId) {
        String auth = SecurityUtils.requireAuthorizationHeader();
        return manageClient.getMaterial(connectionId, auth);
    }
}
