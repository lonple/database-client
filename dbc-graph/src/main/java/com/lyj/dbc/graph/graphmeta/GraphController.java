package com.lyj.dbc.graph.graphmeta;

import com.lyj.dbc.graph.common.api.ApiResponse;
import com.lyj.dbc.graph.graphmeta.dto.GraphCreateRequest;
import com.lyj.dbc.graph.graphmeta.dto.GraphUpdateRequest;
import com.lyj.dbc.graph.graphmeta.dto.TableRelationImportRequest;
import com.lyj.dbc.graph.graphmeta.dto.TableRelationImportResult;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/graphs")
public class GraphController {
    private final GraphService graphService;
    private final TableRelationImportService tableRelationImportService;

    public GraphController(GraphService graphService, TableRelationImportService tableRelationImportService) {
        this.graphService = graphService;
        this.tableRelationImportService = tableRelationImportService;
    }

    @GetMapping
    public ApiResponse<List<GraphEntity>> list(
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String productName,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String code) {
        return ApiResponse.ok(graphService.list(categoryId, productName, keyword, code));
    }

    @GetMapping("/by-code/{code}")
    public ApiResponse<GraphEntity> byCode(@PathVariable String code) {
        return ApiResponse.ok(graphService.requireByCode(code));
    }

    @GetMapping("/{id}")
    public ApiResponse<GraphEntity> get(@PathVariable Long id) {
        return ApiResponse.ok(graphService.require(id));
    }

    @PostMapping
    public ApiResponse<GraphEntity> create(@RequestBody GraphCreateRequest req) {
        return ApiResponse.ok(graphService.create(req));
    }

    /**
     * 从 Markdown 导入库表关系（建图谱 + 表节点 + FK 双向边）。
     * 格式见 demo-company/metadata/table-relations.import.md
     */
    @PostMapping("/import-md")
    public ApiResponse<TableRelationImportResult> importMd(@RequestBody TableRelationImportRequest req) {
        return ApiResponse.ok(tableRelationImportService.importMarkdown(req));
    }

    @PatchMapping("/{id}")
    public ApiResponse<GraphEntity> update(@PathVariable Long id, @RequestBody GraphUpdateRequest req) {
        return ApiResponse.ok(graphService.update(id, req));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        graphService.delete(id);
        return ApiResponse.ok(null);
    }
}
