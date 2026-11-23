package com.lyj.dbc.knowledge.knowledge.controller;

import com.lyj.dbc.knowledge.common.api.ApiResponse;
import com.lyj.dbc.knowledge.knowledge.domain.Relation;
import com.lyj.dbc.knowledge.knowledge.service.IngestService;
import com.lyj.dbc.knowledge.knowledge.service.RelationService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class IngestRelationController {
    private final RelationService relationService;
    private final IngestService ingestService;

    public IngestRelationController(RelationService relationService, IngestService ingestService) {
        this.relationService = relationService;
        this.ingestService = ingestService;
    }

    @PostMapping("/relations")
    public ApiResponse<List<Relation>> relations(@RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
        if (items == null) {
            items = List.of(body);
        }
        return ApiResponse.ok(relationService.createBatch(items));
    }

    @PostMapping("/ingest/md")
    public ApiResponse<Map<String, Object>> ingestMd(@RequestBody Map<String, Object> body) {
        boolean suggest = body.get("suggest") == null || Boolean.parseBoolean(String.valueOf(body.get("suggest")));
        return ApiResponse.ok(ingestService.ingestMd(
                str(body.get("title")),
                str(body.get("body")),
                str(body.get("orientation")),
                suggest,
                str(body.get("productName")),
                str(body.get("summary")),
                str(body.get("sliceRule"))));
    }

    @PostMapping("/ingest/mcp")
    public ApiResponse<Map<String, Object>> ingestMcp(@RequestBody Map<String, Object> body) {
        List<Long> expireSliceIds = parseLongList(body.get("expireSliceIds"));
        Long replaceDocumentId = body.get("replaceDocumentId") != null
                ? Long.valueOf(String.valueOf(body.get("replaceDocumentId")))
                : (body.get("replacesDocumentId") != null
                ? Long.valueOf(String.valueOf(body.get("replacesDocumentId"))) : null);
        return ApiResponse.ok(ingestService.ingestMcp(
                str(body.get("title")),
                str(body.get("body")),
                str(body.get("orientation")),
                str(body.get("productName")),
                str(body.get("summary")),
                str(body.get("updateMode")),
                replaceDocumentId,
                expireSliceIds,
                str(body.get("sliceRule"))));
    }

    private static String str(Object o) {
        return o == null ? null : String.valueOf(o);
    }

    @SuppressWarnings("unchecked")
    private static List<Long> parseLongList(Object raw) {
        if (raw == null) {
            return List.of();
        }
        if (raw instanceof List<?> list) {
            List<Long> out = new java.util.ArrayList<>();
            for (Object o : list) {
                if (o != null) {
                    out.add(Long.valueOf(String.valueOf(o)));
                }
            }
            return out;
        }
        return List.of();
    }
}
