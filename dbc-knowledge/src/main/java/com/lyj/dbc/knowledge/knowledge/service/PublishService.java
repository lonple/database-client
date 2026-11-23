package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import com.lyj.dbc.knowledge.knowledge.mapper.DocumentMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.SliceMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.UnitIndexMapper;
import com.lyj.dbc.knowledge.knowledge.support.ExpireSliceIdsSupport;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class PublishService {
    private final DocumentMapper documentMapper;
    private final SliceMapper sliceMapper;
    private final UnitIndexMapper unitIndexMapper;
    private final DocumentService documentService;
    private final VectorSyncService vectorSyncService;

    public PublishService(DocumentMapper documentMapper,
                          SliceMapper sliceMapper,
                          UnitIndexMapper unitIndexMapper,
                          DocumentService documentService,
                          VectorSyncService vectorSyncService) {
        this.documentMapper = documentMapper;
        this.sliceMapper = sliceMapper;
        this.unitIndexMapper = unitIndexMapper;
        this.documentService = documentService;
        this.vectorSyncService = vectorSyncService;
    }

    /** 发布前预览将过期的原文/切片（供 Console 确认） */
    public Map<String, Object> previewDeprecate(Long documentId) {
        Document doc = documentService.require(documentId);
        Map<String, Object> result = new HashMap<>();
        result.put("updateMode", normalizeMode(doc.getUpdateMode()));
        result.put("document", null);
        result.put("slices", List.of());

        String mode = normalizeMode(doc.getUpdateMode());
        if (KnowledgeEnums.UPDATE_CREATE.equals(mode) || doc.getReplacesDocumentId() == null) {
            return result;
        }
        Document target = documentMapper.selectById(doc.getReplacesDocumentId());
        if (target == null) {
            return result;
        }
        if (KnowledgeEnums.UPDATE_REPLACE_DOCUMENT.equals(mode)) {
            result.put("document", briefDoc(target));
            List<Slice> slices = documentService.listSlices(target.getId());
            result.put("slices", slices.stream().map(this::briefSlice).toList());
            return result;
        }
        if (KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(mode)) {
            List<Long> ids = ExpireSliceIdsSupport.fromJson(doc.getExpireSliceIds());
            List<Map<String, Object>> briefs = new ArrayList<>();
            for (Long sid : ids) {
                Slice s = sliceMapper.selectById(sid);
                if (s != null) {
                    briefs.add(briefSlice(s));
                }
            }
            result.put("slices", briefs);
        }
        return result;
    }

    @Transactional
    public Document publish(Long documentId) {
        Document draft = documentService.require(documentId);
        if (!StringUtils.hasText(draft.getSummary())) {
            throw new BizException("原文简介不能为空");
        }
        String mode = normalizeMode(draft.getUpdateMode());
        List<Slice> draftSlices = documentService.listSlices(documentId);
        validatePublish(draft, draftSlices);

        OffsetDateTime now = OffsetDateTime.now();
        Set<Long> syncDocIds = new HashSet<>();

        if (KnowledgeEnums.UPDATE_REPLACE_DOCUMENT.equals(mode)) {
            Document old = requirePublishedTarget(draft.getReplacesDocumentId());
            draft.setLineageId(old.getLineageId() != null ? old.getLineageId() : old.getId());
            draft.setVersionNo(nextVersion(draft.getLineageId()));
            deprecateDocumentCascade(old, now);
            syncDocIds.add(old.getId());
            publishDocumentInPlace(draft, draftSlices, now);
            syncDocIds.add(draft.getId());
        } else if (KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(mode)) {
            Document target = requirePublishedTarget(draft.getReplacesDocumentId());
            int newVersion = nextVersion(target.getLineageId() != null ? target.getLineageId() : target.getId());
            List<Long> expireIds = ExpireSliceIdsSupport.fromJson(draft.getExpireSliceIds());
            deprecateSlices(expireIds, target.getId(), now);
            // 将草稿切片并入目标原文
            for (Slice s : draftSlices) {
                s.setDocumentId(target.getId());
                s.setStatus(KnowledgeEnums.STATUS_PUBLISHED);
                s.setVersionNo(newVersion);
                s.setPublishedAt(now);
                s.setUpdatedAt(now);
                sliceMapper.updateById(s);
            }
            target.setVersionNo(newVersion);
            target.setUpdatedAt(now);
            target.setVectorSyncStatus(com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent.DOC_SYNC_PENDING);
            documentMapper.updateById(target);
            rebuildUnitIndex(target);
            // 消费掉工作草稿（过期空壳，不入检索）
            draft.setStatus(KnowledgeEnums.STATUS_DEPRECATED);
            draft.setUpdatedAt(now);
            draft.setExpireSliceIds("[]");
            documentMapper.updateById(draft);
            unitIndexMapper.deleteByDocumentId(draft.getId());
            syncDocIds.add(target.getId());
            syncDocIds.add(draft.getId());
            for (Long id : syncDocIds) {
                if (id.equals(draft.getId())) {
                    vectorSyncService.enqueueDeleteAfterCommit(id);
                } else {
                    vectorSyncService.enqueueUpsertAfterCommit(id);
                }
            }
            return target;
        } else {
            // CREATE
            if (draft.getLineageId() == null) {
                draft.setLineageId(draft.getId());
            }
            if (draft.getVersionNo() == null || draft.getVersionNo() < 1) {
                draft.setVersionNo(1);
            }
            publishDocumentInPlace(draft, draftSlices, now);
            syncDocIds.add(draft.getId());
        }

        for (Long id : syncDocIds) {
            Document d = documentMapper.selectById(id);
            if (d != null && KnowledgeEnums.STATUS_PUBLISHED.equals(d.getStatus())) {
                vectorSyncService.enqueueUpsertAfterCommit(id);
            } else {
                vectorSyncService.enqueueDeleteAfterCommit(id);
            }
        }
        return documentMapper.selectById(
                KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(mode) && draft.getReplacesDocumentId() != null
                        ? draft.getReplacesDocumentId() : documentId);
    }

    private void publishDocumentInPlace(Document doc, List<Slice> slices, OffsetDateTime now) {
        doc.setStatus(KnowledgeEnums.STATUS_PUBLISHED);
        doc.setPublishedAt(now);
        doc.setUpdatedAt(now);
        doc.setVectorSyncStatus(com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent.DOC_SYNC_PENDING);
        if (doc.getLineageId() == null) {
            doc.setLineageId(doc.getId());
        }
        if (doc.getVersionNo() == null) {
            doc.setVersionNo(1);
        }
        documentMapper.updateById(doc);

        for (Slice s : slices) {
            s.setStatus(KnowledgeEnums.STATUS_PUBLISHED);
            s.setVersionNo(doc.getVersionNo());
            s.setPublishedAt(now);
            s.setUpdatedAt(now);
            sliceMapper.updateById(s);
        }
        rebuildUnitIndex(doc);
    }

    private void rebuildUnitIndex(Document doc) {
        Long documentId = doc.getId();
        unitIndexMapper.deleteByDocumentId(documentId);
        // 原文自身也进 unit_index（浏览/原文向量）
        // DOCUMENT: description 存原文简介；bodySummary 空
        upsertUnit(KnowledgeEnums.KIND_DOCUMENT, doc.getId(), null,
                doc.getTitle(), doc.getSummary(), "", doc.getBody(), doc.getCategoryId(), List.of(),
                KnowledgeEnums.STATUS_PUBLISHED);

        List<Slice> slices = documentService.listSlices(documentId).stream()
                .filter(s -> KnowledgeEnums.STATUS_PUBLISHED.equals(s.getStatus())
                        || KnowledgeEnums.STATUS_DEPRECATED.equals(s.getStatus()))
                .toList();
        for (Slice s : slices) {
            // 仅已发布切片进索引（过期切片保留在 t_knowledge_slice，浏览直接查表）
            if (!KnowledgeEnums.STATUS_PUBLISHED.equals(s.getStatus())) {
                continue;
            }
            upsertUnit(KnowledgeEnums.KIND_SLICE, s.getId(), doc.getId(),
                    s.getTitle(),
                    s.getDescription() == null ? "" : s.getDescription(),
                    s.getBodySummary() == null ? "" : s.getBodySummary(),
                    s.getBody(), s.getCategoryId(),
                    s.getTechTags() == null ? List.of() : s.getTechTags(),
                    KnowledgeEnums.STATUS_PUBLISHED);
        }
    }

    private void deprecateDocumentCascade(Document old, OffsetDateTime now) {
        old.setStatus(KnowledgeEnums.STATUS_DEPRECATED);
        old.setUpdatedAt(now);
        old.setVectorSyncStatus(com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent.DOC_SYNC_PENDING);
        documentMapper.updateById(old);
        List<Slice> slices = documentService.listSlices(old.getId());
        for (Slice s : slices) {
            if (KnowledgeEnums.STATUS_DEPRECATED.equals(s.getStatus())) {
                continue;
            }
            s.setStatus(KnowledgeEnums.STATUS_DEPRECATED);
            s.setUpdatedAt(now);
            sliceMapper.updateById(s);
        }
        unitIndexMapper.deleteByDocumentId(old.getId());
    }

    private void deprecateSlices(List<Long> sliceIds, Long expectedDocumentId, OffsetDateTime now) {
        for (Long sid : sliceIds) {
            Slice s = sliceMapper.selectById(sid);
            if (s == null) {
                continue;
            }
            if (!expectedDocumentId.equals(s.getDocumentId())) {
                throw new BizException("待过期切片不属于目标原文: " + sid);
            }
            s.setStatus(KnowledgeEnums.STATUS_DEPRECATED);
            s.setUpdatedAt(now);
            sliceMapper.updateById(s);
            unitIndexMapper.deleteByKindAndRef(KnowledgeEnums.KIND_SLICE, sid);
        }
    }

    private Document requirePublishedTarget(Long id) {
        if (id == null) {
            throw new BizException("更新发布需要指定 replacesDocumentId");
        }
        Document target = documentMapper.selectById(id);
        if (target == null) {
            throw new BizException(404, "更新目标原文不存在");
        }
        if (!KnowledgeEnums.STATUS_PUBLISHED.equals(target.getStatus())) {
            throw new BizException("更新目标原文必须为已发布状态");
        }
        return target;
    }

    private int nextVersion(Long lineageId) {
        List<Document> siblings = documentMapper.selectList(new LambdaQueryWrapper<Document>()
                .eq(Document::getLineageId, lineageId)
                .orderByDesc(Document::getVersionNo)
                .last("LIMIT 1"));
        if (siblings.isEmpty() || siblings.get(0).getVersionNo() == null) {
            return 1;
        }
        return siblings.get(0).getVersionNo() + 1;
    }

    @Transactional
    public Document unpublish(Long documentId) {
        Document doc = documentService.require(documentId);
        if (!KnowledgeEnums.STATUS_PUBLISHED.equals(doc.getStatus())) {
            throw new BizException("仅已发布知识可取消发布");
        }
        doc.setStatus(KnowledgeEnums.STATUS_DRAFT);
        doc.setPublishedAt(null);
        doc.setUpdatedAt(OffsetDateTime.now());
        doc.setVectorSyncStatus(com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent.DOC_SYNC_PENDING);
        documentMapper.updateById(doc);

        List<Slice> slices = documentService.listSlices(documentId);
        for (Slice s : slices) {
            if (KnowledgeEnums.STATUS_DEPRECATED.equals(s.getStatus())) {
                continue;
            }
            s.setStatus(KnowledgeEnums.STATUS_DRAFT);
            s.setPublishedAt(null);
            s.setUpdatedAt(OffsetDateTime.now());
            sliceMapper.updateById(s);
        }
        unitIndexMapper.deleteByDocumentId(documentId);
        vectorSyncService.enqueueDeleteAfterCommit(documentId);
        return doc;
    }

    private void validatePublish(Document doc, List<Slice> slices) {
        boolean wantH = KnowledgeEnums.wantsHorizontal(doc.getOrientation());
        boolean wantV = KnowledgeEnums.wantsVertical(doc.getOrientation());

        for (Slice s : slices) {
            String o = s.getOrientation() == null ? KnowledgeEnums.ORIENT_HORIZONTAL : s.getOrientation();
            if (!KnowledgeEnums.isValidSliceOrientation(o)) {
                throw new BizException("切片「" + s.getTitle() + "」取向无效");
            }
            if (!StringUtils.hasText(s.getBody())) {
                throw new BizException("切片「" + s.getTitle() + "」正文不能为空");
            }
        }

        long hCount = slices.stream()
                .filter(s -> KnowledgeEnums.ORIENT_HORIZONTAL.equals(
                        s.getOrientation() == null ? KnowledgeEnums.ORIENT_HORIZONTAL : s.getOrientation()))
                .count();
        long vCount = slices.stream()
                .filter(s -> KnowledgeEnums.ORIENT_VERTICAL.equals(s.getOrientation()))
                .count();

        String mode = normalizeMode(doc.getUpdateMode());
        // REPLACE_SLICES 最终并入目标原文，草稿可不挂分类
        if (KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(mode)) {
            if (slices.isEmpty() && ExpireSliceIdsSupport.fromJson(doc.getExpireSliceIds()).isEmpty()) {
                throw new BizException("切片更新至少需要新增切片或指定过期切片");
            }
            return;
        }

        if (slices.isEmpty()) {
            if (!wantV && wantH) {
                throw new BizException("期望横向切片时，发布前至少需要 1 个横向切片");
            }
            if (doc.getCategoryId() == null) {
                throw new BizException("无切片发布时，请为原文指定业务分类");
            }
            return;
        }

        if (wantH && hCount == 0 && !wantV) {
            throw new BizException("期望横向时至少需要 1 个横向切片");
        }
        if (wantH && hCount == 0 && wantV && vCount == 0) {
            throw new BizException("请至少保留横向或纵向切片之一");
        }
    }

    private Long upsertUnit(String kind, Long refId, Long documentId,
                            String title, String description, String bodySummary, String body,
                            Long categoryId, List<String> techTags, String status) {
        UnitIndex unit = new UnitIndex();
        unit.setKind(kind);
        unit.setRefId(refId);
        unit.setDocumentId(documentId);
        unit.setTitle(title);
        unit.setDescription(description == null ? "" : description);
        unit.setBodySummary(bodySummary == null ? "" : bodySummary);
        unit.setBody(body == null ? "" : body);
        unit.setCategoryId(categoryId);
        unit.setStatus(status);
        unit.setTechTags(techTags);
        unit.setUpdatedAt(OffsetDateTime.now());
        unitIndexMapper.insert(unit);
        return unit.getId();
    }

    private static String normalizeMode(String mode) {
        if (!StringUtils.hasText(mode)) {
            return KnowledgeEnums.UPDATE_CREATE;
        }
        String m = mode.trim().toUpperCase();
        return KnowledgeEnums.isValidUpdateMode(m) ? m : KnowledgeEnums.UPDATE_CREATE;
    }

    private Map<String, Object> briefDoc(Document d) {
        Map<String, Object> m = new HashMap<>();
        m.put("id", d.getId());
        m.put("kind", KnowledgeEnums.KIND_DOCUMENT);
        m.put("title", d.getTitle());
        m.put("summary", d.getSummary());
        m.put("status", d.getStatus());
        m.put("versionNo", d.getVersionNo());
        m.put("lineageId", d.getLineageId());
        return m;
    }

    private Map<String, Object> briefSlice(Slice s) {
        Map<String, Object> m = new HashMap<>();
        m.put("id", s.getId());
        m.put("kind", KnowledgeEnums.KIND_SLICE);
        m.put("documentId", s.getDocumentId());
        m.put("title", s.getTitle());
        m.put("description", s.getDescription());
        m.put("bodySummary", s.getBodySummary());
        m.put("status", s.getStatus());
        m.put("versionNo", s.getVersionNo());
        m.put("seqNo", s.getSeqNo());
        return m;
    }
}
