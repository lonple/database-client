package com.lyj.dbc.knowledge.knowledge.service;

import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentCreateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceVo;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class IngestService {
    private final DocumentService documentService;
    private final SliceSuggestService sliceSuggestService;

    public IngestService(DocumentService documentService, SliceSuggestService sliceSuggestService) {
        this.documentService = documentService;
        this.sliceSuggestService = sliceSuggestService;
    }

    @Transactional
    public Map<String, Object> ingestMd(String title, String body, String orientation, boolean suggest,
                                        String productName, String summary, String sliceRule) {
        DocumentCreateRequest req = new DocumentCreateRequest();
        req.setTitle(title == null || title.isBlank() ? "MD Import" : title);
        req.setProductName(productName);
        req.setSummary(requireSummary(summary));
        req.setBody(body == null ? "" : body);
        req.setOrientation(orientation == null || orientation.isBlank() ? KnowledgeEnums.ORIENT_BOTH : orientation);
        req.setSourceType(KnowledgeEnums.SOURCE_MD_IMPORT);
        Document doc = documentService.create(req);
        List<SliceVo> slices = List.of();
        if (suggest) {
            slices = sliceSuggestService.suggestAndSave(doc.getId(), true, sliceRule);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("document", documentService.detail(doc.getId()));
        result.put("slices", slices);
        return result;
    }

    @Transactional
    public Map<String, Object> ingestMcp(String title, String body, String orientation, String productName, String summary,
                                         String updateMode, Long replaceDocumentId, List<Long> expireSliceIds,
                                         String sliceRule) {
        String mode = StringUtils.hasText(updateMode) ? updateMode.trim().toUpperCase() : KnowledgeEnums.UPDATE_CREATE;
        DocumentCreateRequest req = new DocumentCreateRequest();
        req.setTitle(title == null || title.isBlank() ? "MCP Draft" : title);
        req.setProductName(productName);
        req.setSummary(requireSummary(summary));
        req.setBody(body == null ? "" : body);
        req.setOrientation(orientation == null || orientation.isBlank() ? KnowledgeEnums.ORIENT_BOTH : orientation);
        req.setSourceType(KnowledgeEnums.SOURCE_MCP);
        req.setUpdateMode(mode);
        req.setReplacesDocumentId(replaceDocumentId);
        req.setExpireSliceIds(expireSliceIds == null ? new ArrayList<>() : expireSliceIds);
        Document doc = documentService.create(req);
        List<SliceVo> slices = sliceSuggestService.suggestAndSave(doc.getId(), true, sliceRule);
        Map<String, Object> result = new HashMap<>();
        result.put("documentId", doc.getId());
        result.put("productName", doc.getProductName());
        result.put("status", doc.getStatus());
        result.put("updateMode", doc.getUpdateMode());
        result.put("replacesDocumentId", doc.getReplacesDocumentId());
        result.put("expireSliceIds", req.getExpireSliceIds());
        result.put("note", "DRAFT only. Publish and deprecate via Console.");
        result.put("slices", slices);
        return result;
    }

    private static String requireSummary(String summary) {
        if (!StringUtils.hasText(summary)) {
            throw new com.lyj.dbc.knowledge.common.api.BizException("summary（简介）不能为空");
        }
        return summary.trim();
    }
}
