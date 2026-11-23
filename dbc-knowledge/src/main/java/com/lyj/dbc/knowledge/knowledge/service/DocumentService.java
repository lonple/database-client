package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.Relation;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentCreateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentDetailVo;
import com.lyj.dbc.knowledge.knowledge.dto.DocumentUpdateRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceBatchSaveRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceSaveItem;
import com.lyj.dbc.knowledge.knowledge.dto.SliceVo;
import com.lyj.dbc.knowledge.knowledge.mapper.DocumentMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.RelationMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.SliceMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.UnitIndexMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class DocumentService {
    private final DocumentMapper documentMapper;
    private final SliceMapper sliceMapper;
    private final UnitIndexMapper unitIndexMapper;
    private final RelationMapper relationMapper;
    private final CategoryService categoryService;
    private final VectorSyncService vectorSyncService;

    public DocumentService(DocumentMapper documentMapper,
                           SliceMapper sliceMapper,
                           UnitIndexMapper unitIndexMapper,
                           RelationMapper relationMapper,
                           CategoryService categoryService,
                           VectorSyncService vectorSyncService) {
        this.documentMapper = documentMapper;
        this.sliceMapper = sliceMapper;
        this.unitIndexMapper = unitIndexMapper;
        this.relationMapper = relationMapper;
        this.categoryService = categoryService;
        this.vectorSyncService = vectorSyncService;
    }

    @Transactional
    public Document create(DocumentCreateRequest req) {
        if (!StringUtils.hasText(req.getSummary())) {
            throw new BizException("原文简介不能为空");
        }
        String orientation = resolveDocumentOrientation(req.getOrientations(), req.getOrientation());
        String updateMode = StringUtils.hasText(req.getUpdateMode())
                ? req.getUpdateMode().trim().toUpperCase()
                : KnowledgeEnums.UPDATE_CREATE;
        if (!KnowledgeEnums.isValidUpdateMode(updateMode)) {
            throw new BizException("updateMode 无效");
        }
        Document doc = new Document();
        doc.setTitle(req.getTitle().trim());
        doc.setProductName(trimToNull(req.getProductName()));
        doc.setOrientation(orientation);
        doc.setBody(req.getBody() == null ? "" : req.getBody());
        doc.setSummary(req.getSummary().trim());
        doc.setCategoryId(req.getCategoryId());
        doc.setSourceType(StringUtils.hasText(req.getSourceType()) ? req.getSourceType() : KnowledgeEnums.SOURCE_MANUAL);
        doc.setCreatedBy(req.getCreatedBy());
        doc.setStatus(KnowledgeEnums.STATUS_DRAFT);
        doc.setVectorSyncStatus(com.lyj.dbc.knowledge.knowledge.domain.VectorSyncEvent.DOC_SYNC_NONE);
        doc.setUpdateMode(updateMode);
        doc.setReplacesDocumentId(req.getReplacesDocumentId());
        doc.setExpireSliceIds(com.lyj.dbc.knowledge.knowledge.support.ExpireSliceIdsSupport.toJson(req.getExpireSliceIds()));
        doc.setVersionNo(1);
        doc.setCreatedAt(OffsetDateTime.now());
        doc.setUpdatedAt(OffsetDateTime.now());
        applyUpdateLinkage(doc, updateMode);
        documentMapper.insert(doc);
        if (doc.getLineageId() == null) {
            doc.setLineageId(doc.getId());
            documentMapper.updateById(doc);
        }
        return doc;
    }

    private void applyUpdateLinkage(Document doc, String updateMode) {
        if (KnowledgeEnums.UPDATE_CREATE.equals(updateMode)) {
            return;
        }
        if (doc.getReplacesDocumentId() == null) {
            throw new BizException("更新模式必须指定 replacesDocumentId");
        }
        Document target = require(doc.getReplacesDocumentId());
        if (!KnowledgeEnums.STATUS_PUBLISHED.equals(target.getStatus())) {
            throw new BizException("更新目标必须是已发布原文");
        }
        doc.setLineageId(target.getLineageId() != null ? target.getLineageId() : target.getId());
        if (KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(updateMode)) {
            List<Long> ids = com.lyj.dbc.knowledge.knowledge.support.ExpireSliceIdsSupport.fromJson(doc.getExpireSliceIds());
            for (Long sid : ids) {
                Slice s = sliceMapper.selectById(sid);
                if (s == null || !target.getId().equals(s.getDocumentId())) {
                    throw new BizException("expireSliceIds 必须属于目标原文: " + sid);
                }
            }
        }
    }

    public List<Map<String, Object>> list(String status, Long categoryId) {
        LambdaQueryWrapper<Document> q = new LambdaQueryWrapper<Document>().orderByDesc(Document::getId);
        if (categoryId != null) {
            q.eq(Document::getCategoryId, categoryId);
        }
        if (StringUtils.hasText(status)) {
            q.eq(Document::getStatus, status);
        } else {
            // 原文管理默认不展示已过期；历史版本弹窗可查
            q.ne(Document::getStatus, KnowledgeEnums.STATUS_DEPRECATED);
        }
        List<Document> docs = documentMapper.selectList(q);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Document d : docs) {
            Long sliceCount = sliceMapper.selectCount(new LambdaQueryWrapper<Slice>().eq(Slice::getDocumentId, d.getId()));
            Map<String, Object> row = new HashMap<>();
            row.put("id", d.getId());
            row.put("title", d.getTitle());
            row.put("productName", d.getProductName());
            row.put("orientation", d.getOrientation());
            row.put("status", d.getStatus());
            row.put("sourceType", d.getSourceType());
            row.put("categoryId", d.getCategoryId());
            row.put("sliceCount", sliceCount);
            row.put("vectorSyncStatus", d.getVectorSyncStatus());
            row.put("lineageId", d.getLineageId());
            row.put("versionNo", d.getVersionNo());
            row.put("updateMode", d.getUpdateMode());
            row.put("updatedAt", d.getUpdatedAt());
            result.add(row);
        }
        return result;
    }

    /** 按功能浏览：已发布原文。分类命中该原文自身分类，或任一已发布切片的分类。 */
    public Map<String, Object> pagePublished(Long categoryId, String q, int page, int size) {
        int p = Math.max(page, 1);
        int s = Math.min(Math.max(size, 1), 50);
        LambdaQueryWrapper<Document> w = new LambdaQueryWrapper<Document>()
                .eq(Document::getStatus, KnowledgeEnums.STATUS_PUBLISHED)
                .orderByDesc(Document::getUpdatedAt);
        if (StringUtils.hasText(q)) {
            String kw = q.trim();
            w.and(x -> x.like(Document::getTitle, kw)
                    .or().like(Document::getProductName, kw)
                    .or().like(Document::getSummary, kw));
        }
        if (categoryId != null) {
            List<Slice> inCat = sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                    .eq(Slice::getStatus, KnowledgeEnums.STATUS_PUBLISHED)
                    .eq(Slice::getCategoryId, categoryId));
            Set<Long> docIds = inCat.stream().map(Slice::getDocumentId).filter(Objects::nonNull).collect(Collectors.toSet());
            w.and(x -> {
                x.eq(Document::getCategoryId, categoryId);
                if (!docIds.isEmpty()) {
                    x.or().in(Document::getId, docIds);
                }
            });
        }
        List<Document> all = documentMapper.selectList(w);
        int from = Math.min((p - 1) * s, all.size());
        int to = Math.min(from + s, all.size());
        List<Map<String, Object>> records = new ArrayList<>();
        for (Document d : all.subList(from, to)) {
            Map<String, Object> row = new HashMap<>();
            row.put("id", d.getId());
            row.put("title", d.getTitle());
            row.put("productName", d.getProductName());
            row.put("summary", d.getSummary());
            row.put("status", d.getStatus());
            row.put("lineageId", d.getLineageId());
            row.put("versionNo", d.getVersionNo());
            records.add(row);
        }
        Map<String, Object> pageResult = new HashMap<>();
        pageResult.put("records", records);
        pageResult.put("total", all.size());
        pageResult.put("page", p);
        pageResult.put("size", s);
        return pageResult;
    }

    /** 某原文下已发布 + 已过期切片（过期仍展示，带 status） */
    public Map<String, Object> pagePublishedSlices(Long documentId, Long categoryId, int page, int size) {
        Document doc = require(documentId);
        if (KnowledgeEnums.STATUS_DEPRECATED.equals(doc.getStatus())) {
            Map<String, Object> empty = new HashMap<>();
            empty.put("records", List.of());
            empty.put("total", 0);
            empty.put("page", Math.max(page, 1));
            empty.put("size", Math.min(Math.max(size, 1), 50));
            return empty;
        }
        int p = Math.max(page, 1);
        int s = Math.min(Math.max(size, 1), 50);
        LambdaQueryWrapper<Slice> w = new LambdaQueryWrapper<Slice>()
                .eq(Slice::getDocumentId, documentId)
                .in(Slice::getStatus, List.of(KnowledgeEnums.STATUS_PUBLISHED, KnowledgeEnums.STATUS_DEPRECATED))
                .orderByAsc(Slice::getSeqNo)
                .orderByAsc(Slice::getId);
        if (categoryId != null) {
            w.eq(Slice::getCategoryId, categoryId);
        }
        List<Slice> all = sliceMapper.selectList(w);
        int from = Math.min((p - 1) * s, all.size());
        int to = Math.min(from + s, all.size());
        List<Map<String, Object>> records = new ArrayList<>();
        for (Slice slice : all.subList(from, to)) {
            Map<String, Object> row = new HashMap<>();
            row.put("id", slice.getId());
            row.put("documentId", slice.getDocumentId());
            row.put("title", slice.getTitle());
            row.put("description", slice.getDescription());
            row.put("bodySummary", slice.getBodySummary());
            row.put("seqNo", slice.getSeqNo());
            row.put("status", slice.getStatus());
            row.put("versionNo", slice.getVersionNo());
            records.add(row);
        }
        Map<String, Object> pageResult = new HashMap<>();
        pageResult.put("records", records);
        pageResult.put("total", all.size());
        pageResult.put("page", p);
        pageResult.put("size", s);
        return pageResult;
    }

    public DocumentDetailVo detail(Long id) {
        Document doc = require(id);
        DocumentDetailVo vo = toDetail(doc);
        List<Slice> slices = sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                .eq(Slice::getDocumentId, id)
                .orderByAsc(Slice::getSeqNo)
                .orderByAsc(Slice::getId));
        vo.setSlices(slices.stream().map(this::toSliceVo).toList());
        return vo;
    }

    @Transactional
    public Document update(Long id, DocumentUpdateRequest req) {
        Document doc = require(id);
        if (KnowledgeEnums.STATUS_PUBLISHED.equals(doc.getStatus())) {
            throw new BizException("已发布原文请先取消发布再编辑");
        }
        if (StringUtils.hasText(req.getTitle())) {
            doc.setTitle(req.getTitle().trim());
        }
        if (req.getProductName() != null) {
            doc.setProductName(trimToNull(req.getProductName()));
        }
        if (req.getOrientations() != null && !req.getOrientations().isEmpty()) {
            doc.setOrientation(resolveDocumentOrientation(req.getOrientations(), null));
        } else if (StringUtils.hasText(req.getOrientation())) {
            doc.setOrientation(resolveDocumentOrientation(null, req.getOrientation()));
        }
        if (req.getBody() != null) {
            doc.setBody(req.getBody());
        }
        if (req.getSummary() != null) {
            if (!StringUtils.hasText(req.getSummary())) {
                throw new BizException("原文简介不能为空");
            }
            doc.setSummary(req.getSummary().trim());
        }
        if (req.getCategoryId() != null) {
            doc.setCategoryId(req.getCategoryId());
        }
        if (StringUtils.hasText(req.getUpdateMode())) {
            String mode = req.getUpdateMode().trim().toUpperCase();
            if (!KnowledgeEnums.isValidUpdateMode(mode)) {
                throw new BizException("updateMode 无效");
            }
            doc.setUpdateMode(mode);
        }
        if (req.getReplacesDocumentId() != null) {
            doc.setReplacesDocumentId(req.getReplacesDocumentId());
        }
        if (req.getExpireSliceIds() != null) {
            doc.setExpireSliceIds(com.lyj.dbc.knowledge.knowledge.support.ExpireSliceIdsSupport.toJson(req.getExpireSliceIds()));
        }
        applyUpdateLinkage(doc, StringUtils.hasText(doc.getUpdateMode()) ? doc.getUpdateMode() : KnowledgeEnums.UPDATE_CREATE);
        doc.setUpdatedAt(OffsetDateTime.now());
        documentMapper.updateById(doc);
        return doc;
    }

    @Transactional
    public List<Slice> saveSlices(Long documentId, SliceBatchSaveRequest req) {
        Document doc = require(documentId);
        if (KnowledgeEnums.STATUS_PUBLISHED.equals(doc.getStatus())) {
            throw new BizException("已发布原文请先取消发布再改切片");
        }
        List<Slice> existing = sliceMapper.selectList(new LambdaQueryWrapper<Slice>().eq(Slice::getDocumentId, documentId));
        Set<Long> keepIds = req.getSlices().stream()
                .map(SliceSaveItem::getId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        for (Slice old : existing) {
            if (!keepIds.contains(old.getId())) {
                sliceMapper.deleteById(old.getId());
            }
        }

        List<Slice> saved = new ArrayList<>();
        int seq = 0;
        for (SliceSaveItem item : req.getSlices()) {
            if (!StringUtils.hasText(item.getTitle())) {
                throw new BizException("切片标题不能为空");
            }
            Slice slice;
            if (item.getId() != null) {
                slice = sliceMapper.selectById(item.getId());
                if (slice == null || !documentId.equals(slice.getDocumentId())) {
                    throw new BizException("切片不存在或不属于该原文");
                }
            } else {
                slice = new Slice();
                slice.setDocumentId(documentId);
                slice.setStatus(KnowledgeEnums.STATUS_DRAFT);
                slice.setCreatedAt(OffsetDateTime.now());
            }
            slice.setSeqNo(item.getSeqNo() != null ? item.getSeqNo() : seq);
            slice.setTitle(item.getTitle().trim());
            String body = item.getBody() == null ? "" : item.getBody();
            slice.setBody(body);
            String description = item.getDescription() == null ? "" : item.getDescription().trim();
            if (!StringUtils.hasText(description)) {
                description = nthNonBlankLine(body, 1, "");
            }
            slice.setDescription(description);
            String bodySummary = item.getBodySummary() == null ? "" : item.getBodySummary().trim();
            if (!StringUtils.hasText(bodySummary)) {
                bodySummary = nthNonBlankLine(body, 2, "");
            }
            slice.setBodySummary(bodySummary);
            slice.setTechTags(item.getTechTags() == null ? List.of() : item.getTechTags());
            String sliceOrient = item.getOrientation();
            if (!StringUtils.hasText(sliceOrient)) {
                sliceOrient = KnowledgeEnums.ORIENT_HORIZONTAL;
            }
            if (!KnowledgeEnums.isValidSliceOrientation(sliceOrient)) {
                throw new BizException("切片取向必须为 HORIZONTAL 或 VERTICAL");
            }
            slice.setOrientation(sliceOrient);
            slice.setCategoryId(item.getCategoryId());
            slice.setUpdatedAt(OffsetDateTime.now());
            if (slice.getId() == null) {
                sliceMapper.insert(slice);
            } else {
                sliceMapper.updateById(slice);
            }
            saved.add(slice);
            seq++;
        }
        doc.setUpdatedAt(OffsetDateTime.now());
        documentMapper.updateById(doc);
        return saved;
    }

    /** 删除原文及其全部切片、检索索引、相关关联 */
    @Transactional
    public void deleteDocument(Long documentId) {
        Document doc = require(documentId);
        List<Slice> slices = listSlices(documentId);
        for (Slice s : slices) {
            removeSliceRelations(s.getId());
            unitIndexMapper.deleteByKindAndRef(KnowledgeEnums.KIND_SLICE, s.getId());
            sliceMapper.deleteById(s.getId());
        }
        removeDocumentRelations(documentId);
        unitIndexMapper.deleteByDocumentId(documentId);
        documentMapper.deleteById(doc.getId());
        vectorSyncService.enqueueDeleteAfterCommit(documentId);
    }

    /** 删除单条切片及其检索索引、相关关联（已发布原文也可删片，需同步索引） */
    @Transactional
    public void deleteSlice(Long documentId, Long sliceId) {
        require(documentId);
        Slice slice = sliceMapper.selectById(sliceId);
        if (slice == null || !documentId.equals(slice.getDocumentId())) {
            throw new BizException(404, "切片不存在或不属于该原文");
        }
        removeSliceRelations(sliceId);
        unitIndexMapper.deleteByKindAndRef(KnowledgeEnums.KIND_SLICE, sliceId);
        sliceMapper.deleteById(sliceId);
        Document doc = require(documentId);
        doc.setUpdatedAt(OffsetDateTime.now());
        documentMapper.updateById(doc);
        if (KnowledgeEnums.STATUS_PUBLISHED.equalsIgnoreCase(doc.getStatus())) {
            vectorSyncService.enqueueUpsertAfterCommit(documentId);
        }
    }

    private void removeSliceRelations(Long sliceId) {
        relationMapper.delete(new LambdaQueryWrapper<Relation>()
                .and(w -> w
                        .eq(Relation::getFromKind, KnowledgeEnums.KIND_SLICE).eq(Relation::getFromId, sliceId)
                        .or()
                        .eq(Relation::getToKind, KnowledgeEnums.KIND_SLICE).eq(Relation::getToId, sliceId)));
    }

    private void removeDocumentRelations(Long documentId) {
        relationMapper.delete(new LambdaQueryWrapper<Relation>()
                .and(w -> w
                        .eq(Relation::getFromKind, KnowledgeEnums.KIND_DOCUMENT).eq(Relation::getFromId, documentId)
                        .or()
                        .eq(Relation::getToKind, KnowledgeEnums.KIND_DOCUMENT).eq(Relation::getToId, documentId)));
    }

    public Document require(Long id) {
        Document doc = documentMapper.selectById(id);
        if (doc == null) {
            throw new BizException(404, "原文不存在: " + id);
        }
        return doc;
    }

    public List<Slice> listSlices(Long documentId) {
        return sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                .eq(Slice::getDocumentId, documentId)
                .orderByAsc(Slice::getSeqNo)
                .orderByAsc(Slice::getId));
    }

    private String resolveDocumentOrientation(List<String> orientations, String orientation) {
        if (orientations != null && !orientations.isEmpty()) {
            return KnowledgeEnums.toDocumentOrientation(orientations);
        }
        if (!StringUtils.hasText(orientation)) {
            return KnowledgeEnums.ORIENT_BOTH;
        }
        if (!KnowledgeEnums.isValidDocumentOrientation(orientation)) {
            throw new BizException("orientation 必须为 HORIZONTAL、VERTICAL 或 BOTH（横向与纵向可并存）");
        }
        return orientation;
    }

    private void validateOrientation(String orientation) {
        resolveDocumentOrientation(null, orientation);
    }

    private DocumentDetailVo toDetail(Document doc) {
        DocumentDetailVo vo = new DocumentDetailVo();
        vo.setId(doc.getId());
        vo.setTitle(doc.getTitle());
        vo.setProductName(doc.getProductName());
        vo.setOrientation(doc.getOrientation());
        vo.setSourceType(doc.getSourceType());
        vo.setBody(doc.getBody());
        vo.setStatus(doc.getStatus());
        vo.setCategoryId(doc.getCategoryId());
        vo.setCategoryPath(categoryService.pathLabel(doc.getCategoryId()));
        vo.setSummary(doc.getSummary());
        vo.setLineageId(doc.getLineageId());
        vo.setVersionNo(doc.getVersionNo());
        vo.setUpdateMode(doc.getUpdateMode());
        vo.setReplacesDocumentId(doc.getReplacesDocumentId());
        vo.setExpireSliceIds(com.lyj.dbc.knowledge.knowledge.support.ExpireSliceIdsSupport.fromJson(doc.getExpireSliceIds()));
        vo.setVectorSyncStatus(doc.getVectorSyncStatus());
        vo.setCreatedAt(doc.getCreatedAt());
        vo.setUpdatedAt(doc.getUpdatedAt());
        vo.setPublishedAt(doc.getPublishedAt());
        return vo;
    }

    private static String trimToNull(String s) {
        if (s == null) {
            return null;
        }
        String t = s.trim();
        return t.isEmpty() ? null : t;
    }

    private SliceVo toSliceVo(Slice s) {
        SliceVo vo = new SliceVo();
        vo.setId(s.getId());
        vo.setDocumentId(s.getDocumentId());
        vo.setSeqNo(s.getSeqNo());
        vo.setTitle(s.getTitle());
        vo.setDescription(s.getDescription());
        vo.setBodySummary(s.getBodySummary());
        vo.setBody(s.getBody());
        vo.setTechTags(s.getTechTags() == null ? List.of() : s.getTechTags());
        vo.setOrientation(s.getOrientation() == null ? KnowledgeEnums.ORIENT_HORIZONTAL : s.getOrientation());
        vo.setCategoryId(s.getCategoryId());
        vo.setCategoryPath(categoryService.pathLabel(s.getCategoryId()));
        vo.setStatus(s.getStatus());
        vo.setVersionNo(s.getVersionNo());
        vo.setPublishedAt(s.getPublishedAt());
        return vo;
    }

    /** 取正文第 n 个非空行（1-based）；不足则回退 fallback。 */
    private static String nthNonBlankLine(String content, int n, String fallback) {
        if (n < 1) {
            return fallback == null ? "" : fallback;
        }
        if (content != null) {
            int found = 0;
            for (String line : content.split("\n", -1)) {
                String trimmed = line == null ? "" : line.trim();
                if (!StringUtils.hasText(trimmed)) {
                    continue;
                }
                found++;
                if (found == n) {
                    return trimmed;
                }
            }
        }
        return fallback == null ? "" : fallback;
    }

    /** 同 lineage 下当前生效（已发布、版本最高）的原文；没有则 null */
    public Map<String, Object> latestPublished(Long documentId) {
        Document doc = require(documentId);
        Long lineageId = doc.getLineageId() != null ? doc.getLineageId() : doc.getId();
        List<Document> list = documentMapper.selectList(new LambdaQueryWrapper<Document>()
                .eq(Document::getLineageId, lineageId)
                .eq(Document::getStatus, KnowledgeEnums.STATUS_PUBLISHED)
                .orderByDesc(Document::getVersionNo)
                .orderByDesc(Document::getId)
                .last("LIMIT 1"));
        if (list.isEmpty()) {
            return null;
        }
        Document latest = list.get(0);
        Map<String, Object> row = new HashMap<>();
        row.put("id", latest.getId());
        row.put("title", latest.getTitle());
        row.put("summary", latest.getSummary());
        row.put("status", latest.getStatus());
        row.put("versionNo", latest.getVersionNo());
        row.put("lineageId", latest.getLineageId());
        row.put("productName", latest.getProductName());
        return row;
    }

    /** 同 lineage 原文版本列表（含过期） */
    public List<Map<String, Object>> listDocumentVersions(Long documentId) {
        Document doc = require(documentId);
        Long lineageId = doc.getLineageId() != null ? doc.getLineageId() : doc.getId();
        List<Document> list = documentMapper.selectList(new LambdaQueryWrapper<Document>()
                .eq(Document::getLineageId, lineageId)
                .orderByDesc(Document::getVersionNo)
                .orderByDesc(Document::getId));
        List<Map<String, Object>> result = new ArrayList<>();
        for (Document d : list) {
            Map<String, Object> row = new HashMap<>();
            row.put("id", d.getId());
            row.put("title", d.getTitle());
            row.put("summary", d.getSummary());
            row.put("status", d.getStatus());
            row.put("versionNo", d.getVersionNo());
            row.put("lineageId", d.getLineageId());
            row.put("publishedAt", d.getPublishedAt());
            row.put("updatedAt", d.getUpdatedAt());
            result.add(row);
        }
        return result;
    }

    /** 同 lineage + 同 seq_no 的切片版本（跨原文版本） */
    public List<Map<String, Object>> listSliceVersions(Long sliceId) {
        Slice slice = sliceMapper.selectById(sliceId);
        if (slice == null) {
            throw new BizException(404, "切片不存在");
        }
        Document doc = require(slice.getDocumentId());
        Long lineageId = doc.getLineageId() != null ? doc.getLineageId() : doc.getId();
        List<Document> docs = documentMapper.selectList(new LambdaQueryWrapper<Document>()
                .eq(Document::getLineageId, lineageId));
        Set<Long> docIds = docs.stream().map(Document::getId).collect(Collectors.toSet());
        if (docIds.isEmpty()) {
            return List.of();
        }
        List<Slice> slices = sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                .in(Slice::getDocumentId, docIds)
                .eq(Slice::getSeqNo, slice.getSeqNo())
                .orderByDesc(Slice::getVersionNo)
                .orderByDesc(Slice::getId));
        // 若 seq 对不上（并入后），退化为按标题匹配
        if (slices.size() <= 1 && StringUtils.hasText(slice.getTitle())) {
            slices = sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                    .in(Slice::getDocumentId, docIds)
                    .eq(Slice::getTitle, slice.getTitle())
                    .orderByDesc(Slice::getVersionNo)
                    .orderByDesc(Slice::getId));
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (Slice s : slices) {
            Map<String, Object> row = new HashMap<>();
            row.put("id", s.getId());
            row.put("documentId", s.getDocumentId());
            row.put("title", s.getTitle());
            row.put("description", s.getDescription());
            row.put("bodySummary", s.getBodySummary());
            row.put("status", s.getStatus());
            row.put("versionNo", s.getVersionNo());
            row.put("seqNo", s.getSeqNo());
            row.put("publishedAt", s.getPublishedAt());
            result.add(row);
        }
        return result;
    }

    /** 从已发布原文发起更新草稿 */
    @Transactional
    public Document startUpdate(Long publishedId, String updateMode, List<Long> expireSliceIds) {
        Document target = require(publishedId);
        if (!KnowledgeEnums.STATUS_PUBLISHED.equals(target.getStatus())) {
            throw new BizException("只能从已发布原文发起更新");
        }
        String mode = StringUtils.hasText(updateMode) ? updateMode.trim().toUpperCase() : KnowledgeEnums.UPDATE_REPLACE_DOCUMENT;
        if (!KnowledgeEnums.UPDATE_REPLACE_DOCUMENT.equals(mode) && !KnowledgeEnums.UPDATE_REPLACE_SLICES.equals(mode)) {
            throw new BizException("updateMode 须为 REPLACE_DOCUMENT 或 REPLACE_SLICES");
        }
        DocumentCreateRequest req = new DocumentCreateRequest();
        req.setTitle(target.getTitle());
        req.setProductName(target.getProductName());
        req.setOrientation(target.getOrientation());
        req.setBody(target.getBody());
        req.setSummary(StringUtils.hasText(target.getSummary()) ? target.getSummary() : "（待补充简介）");
        req.setCategoryId(target.getCategoryId());
        req.setSourceType(target.getSourceType());
        req.setUpdateMode(mode);
        req.setReplacesDocumentId(target.getId());
        req.setExpireSliceIds(expireSliceIds == null ? List.of() : expireSliceIds);
        Document draft = create(req);
        if (KnowledgeEnums.UPDATE_REPLACE_DOCUMENT.equals(mode)) {
            // 复制切片到草稿供校对
            List<Slice> oldSlices = listSlices(target.getId()).stream()
                    .filter(s -> KnowledgeEnums.STATUS_PUBLISHED.equals(s.getStatus()))
                    .toList();
            int seq = 0;
            for (Slice old : oldSlices) {
                Slice neu = new Slice();
                neu.setDocumentId(draft.getId());
                neu.setSeqNo(old.getSeqNo() != null ? old.getSeqNo() : seq);
                neu.setTitle(old.getTitle());
                neu.setDescription(old.getDescription());
                neu.setBodySummary(old.getBodySummary());
                neu.setBody(old.getBody());
                neu.setTechTags(old.getTechTags());
                neu.setOrientation(old.getOrientation());
                neu.setCategoryId(old.getCategoryId());
                neu.setStatus(KnowledgeEnums.STATUS_DRAFT);
                neu.setVersionNo(1);
                neu.setCreatedAt(OffsetDateTime.now());
                neu.setUpdatedAt(OffsetDateTime.now());
                sliceMapper.insert(neu);
                seq++;
            }
        }
        return draft;
    }
}
