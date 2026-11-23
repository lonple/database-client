package com.lyj.dbc.knowledge.knowledge.controller;

import com.lyj.dbc.knowledge.common.api.ApiResponse;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import com.lyj.dbc.knowledge.knowledge.dto.SearchResultVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationQueryRequest;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationQueryResultVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableSearchRequest;
import com.lyj.dbc.knowledge.knowledge.dto.TableSearchResultVo;
import com.lyj.dbc.knowledge.knowledge.service.SearchService;
import com.lyj.dbc.knowledge.knowledge.service.TableSearchService;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class SearchController {
    private final SearchService searchService;
    private final TableSearchService tableSearchService;
    private final com.lyj.dbc.knowledge.knowledge.service.CategoryService categoryService;

    public SearchController(SearchService searchService, TableSearchService tableSearchService,
                            com.lyj.dbc.knowledge.knowledge.service.CategoryService categoryService) {
        this.searchService = searchService;
        this.tableSearchService = tableSearchService;
        this.categoryService = categoryService;
    }

    @GetMapping("/units")
    public ApiResponse<List<UnitIndex>> units(@RequestParam(required = false) Long categoryId,
                                              @RequestParam(required = false) String kind,
                                              @RequestParam(required = false) String status,
                                              @RequestParam(required = false) String q) {
        return ApiResponse.ok(searchService.listUnits(categoryId, kind, status, q));
    }

    @GetMapping("/units/{kind}/{id}")
    public ApiResponse<Map<String, Object>> unitDetail(@PathVariable String kind, @PathVariable Long id) {
        return ApiResponse.ok(searchService.unitDetail(kind.toUpperCase(), id));
    }

    @GetMapping("/search")
    public ApiResponse<SearchResultVo> search(@RequestParam(required = false) String q,
                                              @RequestParam String productName,
                                              @RequestParam(defaultValue = "10") int topK,
                                              @RequestParam(required = false) Long categoryId,
                                              @RequestParam(required = false) String categoryCode,
                                              @RequestParam(required = false) String kinds,
                                              @RequestParam(required = false) String documentIds,
                                              @RequestParam(defaultValue = "true") boolean rewrite,
                                              @RequestParam(defaultValue = "false") boolean includeBody,
                                              @RequestParam(required = false) String titleQuery,
                                              @RequestParam(required = false) String descriptionQuery,
                                              @RequestParam(required = false) String summaryQuery,
                                              @RequestParam(required = false) String bodySummaryQuery,
                                              @RequestParam(required = false) String ftsQuery) {
        // 兼容旧参 summaryQuery → descriptionQuery
        String descQ = StringUtils.hasText(descriptionQuery) ? descriptionQuery : summaryQuery;
        List<String> kindList = kinds == null || kinds.isBlank()
                ? null
                : Arrays.stream(kinds.split(",")).map(String::trim).map(String::toUpperCase).toList();
        List<Long> docIds = parseDocumentIds(documentIds);
        Long resolvedCategoryId = categoryId;
        if (StringUtils.hasText(categoryCode)) {
            resolvedCategoryId = categoryService.requireByCode(categoryCode).getId();
        }
        return ApiResponse.ok(searchService.search(
                q, productName, topK, resolvedCategoryId, kindList, docIds, rewrite,
                titleQuery, descQ, bodySummaryQuery, ftsQuery, includeBody));
    }

    /**
     * 问数表语义找表：分字段检索 + 表名过滤 + 可选图谱邻接展开。
     */
    @PostMapping("/search/tables")
    public ApiResponse<TableSearchResultVo> searchTables(@RequestBody TableSearchRequest body) {
        return ApiResponse.ok(tableSearchService.searchTables(body));
    }

    /**
     * 按一张表查图谱邻接。知识库先调图谱 table-neighbors，再整理成与 search/tables 相同的 tableRelations（含 edges）。
     */
    @PostMapping("/search/table-relations")
    public ApiResponse<TableRelationQueryResultVo> tableRelations(@RequestBody TableRelationQueryRequest body) {
        return ApiResponse.ok(tableSearchService.listTableRelations(body));
    }

    /**
     * null/空白：不过滤文章；非空字符串解析为 id 列表（可为空列表，表示显式无候选）。
     */
    static List<Long> parseDocumentIds(String raw) {
        if (!StringUtils.hasText(raw)) {
            return null;
        }
        return Arrays.stream(raw.split(","))
                .map(String::trim)
                .filter(StringUtils::hasText)
                .map(s -> {
                    try {
                        return Long.valueOf(s);
                    } catch (NumberFormatException e) {
                        throw new IllegalArgumentException("invalid documentIds: " + s);
                    }
                })
                .distinct()
                .toList();
    }
}
