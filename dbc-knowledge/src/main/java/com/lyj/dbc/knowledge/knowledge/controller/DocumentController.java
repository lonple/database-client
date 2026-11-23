package com.lyj.dbc.knowledge.knowledge.controller;

import com.lyj.dbc.knowledge.common.api.ApiResponse;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentCreateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentDetailVo;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentUpdateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceBatchSaveRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceVo;
import com.lyj.dbc.knowledge.knowledge.service.DocumentService;
import com.lyj.dbc.knowledge.knowledge.service.PublishService;
import com.lyj.dbc.knowledge.knowledge.service.SliceSuggestService;
import com.lyj.dbc.knowledge.knowledge.service.VectorSyncService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {
    private final DocumentService documentService;
    private final SliceSuggestService sliceSuggestService;
    private final PublishService publishService;
    private final VectorSyncService vectorSyncService;

    public DocumentController(DocumentService documentService,
                              SliceSuggestService sliceSuggestService,
                              PublishService publishService,
                              VectorSyncService vectorSyncService) {
        this.documentService = documentService;
        this.sliceSuggestService = sliceSuggestService;
        this.publishService = publishService;
        this.vectorSyncService = vectorSyncService;
    }

    @PostMapping
    public ApiResponse<Document> create(@Valid @RequestBody DocumentCreateRequest req) {
        return ApiResponse.ok(documentService.create(req));
    }

    @GetMapping
    public ApiResponse<List<Map<String, Object>>> list(@RequestParam(required = false) String status,
                                                      @RequestParam(required = false) Long categoryId) {
        return ApiResponse.ok(documentService.list(status, categoryId));
    }

    @GetMapping("/published")
    public ApiResponse<Map<String, Object>> published(@RequestParam(required = false) Long categoryId,
                                                      @RequestParam(required = false) String q,
                                                      @RequestParam(defaultValue = "1") int page,
                                                      @RequestParam(defaultValue = "8") int size) {
        return ApiResponse.ok(documentService.pagePublished(categoryId, q, page, size));
    }

    @GetMapping("/{id}/slices/published")
    public ApiResponse<Map<String, Object>> publishedSlices(@PathVariable Long id,
                                                            @RequestParam(required = false) Long categoryId,
                                                            @RequestParam(defaultValue = "1") int page,
                                                            @RequestParam(defaultValue = "8") int size) {
        return ApiResponse.ok(documentService.pagePublishedSlices(id, categoryId, page, size));
    }

    @GetMapping("/{id}")
    public ApiResponse<DocumentDetailVo> detail(@PathVariable Long id) {
        return ApiResponse.ok(documentService.detail(id));
    }

    @PutMapping("/{id}")
    public ApiResponse<Document> update(@PathVariable Long id, @RequestBody DocumentUpdateRequest req) {
        return ApiResponse.ok(documentService.update(id, req));
    }

    @PostMapping("/{id}/suggest-slices")
    public ApiResponse<List<SliceVo>> suggest(@PathVariable Long id,
                                              @RequestParam(defaultValue = "false") boolean force,
                                              @RequestBody(required = false) Map<String, Object> body) {
        String sliceRule = null;
        if (body != null) {
            Object rule = body.get("sliceRule");
            if (rule == null) {
                rule = body.get("slice_rule");
            }
            if (rule != null) {
                String s = String.valueOf(rule).trim();
                if (!s.isEmpty() && !"null".equalsIgnoreCase(s)) {
                    sliceRule = s;
                }
            }
        }
        return ApiResponse.ok(sliceSuggestService.suggestAndSave(id, force, sliceRule));
    }

    @PutMapping("/{id}/slices")
    public ApiResponse<List<Slice>> saveSlices(@PathVariable Long id,
                                               @Valid @RequestBody SliceBatchSaveRequest req) {
        return ApiResponse.ok(documentService.saveSlices(id, req));
    }

    @PostMapping("/{id}/publish")
    public ApiResponse<Document> publish(@PathVariable Long id) {
        return ApiResponse.ok(publishService.publish(id));
    }

    @GetMapping("/{id}/publish-preview")
    public ApiResponse<Map<String, Object>> publishPreview(@PathVariable Long id) {
        return ApiResponse.ok(publishService.previewDeprecate(id));
    }

    @PostMapping("/{id}/start-update")
    public ApiResponse<Document> startUpdate(@PathVariable Long id, @RequestBody(required = false) Map<String, Object> body) {
        String mode = body != null && body.get("updateMode") != null
                ? String.valueOf(body.get("updateMode")) : "REPLACE_DOCUMENT";
        List<Long> expireIds = new java.util.ArrayList<>();
        if (body != null && body.get("expireSliceIds") instanceof List<?> list) {
            for (Object o : list) {
                if (o != null) {
                    expireIds.add(Long.valueOf(String.valueOf(o)));
                }
            }
        }
        return ApiResponse.ok(documentService.startUpdate(id, mode, expireIds));
    }

    @GetMapping("/{id}/versions")
    public ApiResponse<List<Map<String, Object>>> documentVersions(@PathVariable Long id) {
        return ApiResponse.ok(documentService.listDocumentVersions(id));
    }

    @GetMapping("/{id}/latest-published")
    public ApiResponse<Map<String, Object>> latestPublished(@PathVariable Long id) {
        return ApiResponse.ok(documentService.latestPublished(id));
    }

    @GetMapping("/{id}/slices/{sliceId}/versions")
    public ApiResponse<List<Map<String, Object>>> sliceVersions(@PathVariable Long id, @PathVariable Long sliceId) {
        return ApiResponse.ok(documentService.listSliceVersions(sliceId));
    }

    @PostMapping("/{id}/unpublish")
    public ApiResponse<Document> unpublish(@PathVariable Long id) {
        return ApiResponse.ok(publishService.unpublish(id));
    }

    @PostMapping("/{id}/sync-vector")
    public ApiResponse<Document> syncVector(@PathVariable Long id) {
        return ApiResponse.ok(vectorSyncService.manualSync(id));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/{id}/slices/{sliceId}")
    public ApiResponse<Void> deleteSlice(@PathVariable Long id, @PathVariable Long sliceId) {
        documentService.deleteSlice(id, sliceId);
        return ApiResponse.ok(null);
    }
}
