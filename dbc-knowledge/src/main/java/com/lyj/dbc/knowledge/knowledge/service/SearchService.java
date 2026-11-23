package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.Relation;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import com.lyj.dbc.knowledge.knowledge.dto.SearchResultVo;
import com.lyj.dbc.knowledge.knowledge.mapper.DocumentMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.RelationMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.SliceMapper;
import com.lyj.dbc.knowledge.knowledge.mapper.UnitIndexMapper;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusDocumentIndex;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusSliceIndex;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class SearchService {
    private static final Logger log = LoggerFactory.getLogger(SearchService.class);

    private final UnitIndexMapper unitIndexMapper;
    private final EmbeddingService embeddingService;
    private final QueryRewriteService queryRewriteService;
    private final CategoryService categoryService;
    private final DocumentMapper documentMapper;
    private final SliceMapper sliceMapper;
    private final RelationMapper relationMapper;
    private final ObjectProvider<MilvusSliceIndex> milvusSliceIndex;
    private final ObjectProvider<MilvusDocumentIndex> milvusDocumentIndex;
    private final RerankService rerankService;

    public SearchService(UnitIndexMapper unitIndexMapper,
                         EmbeddingService embeddingService,
                         QueryRewriteService queryRewriteService,
                         CategoryService categoryService,
                         DocumentMapper documentMapper,
                         SliceMapper sliceMapper,
                         RelationMapper relationMapper,
                         ObjectProvider<MilvusSliceIndex> milvusSliceIndex,
                         ObjectProvider<MilvusDocumentIndex> milvusDocumentIndex,
                         RerankService rerankService) {
        this.unitIndexMapper = unitIndexMapper;
        this.embeddingService = embeddingService;
        this.queryRewriteService = queryRewriteService;
        this.categoryService = categoryService;
        this.documentMapper = documentMapper;
        this.sliceMapper = sliceMapper;
        this.relationMapper = relationMapper;
        this.milvusSliceIndex = milvusSliceIndex;
        this.milvusDocumentIndex = milvusDocumentIndex;
        this.rerankService = rerankService;
    }

    public List<UnitIndex> listUnits(Long categoryId, String kind, String status, String q) {
        LambdaQueryWrapper<UnitIndex> w = new LambdaQueryWrapper<>();
        w.eq(UnitIndex::getStatus, StringUtils.hasText(status) ? status : KnowledgeEnums.STATUS_PUBLISHED);
        if (categoryId != null) {
            w.eq(UnitIndex::getCategoryId, categoryId);
        }
        if (StringUtils.hasText(kind)) {
            w.eq(UnitIndex::getKind, kind);
        }
        if (StringUtils.hasText(q)) {
            w.and(x -> x.like(UnitIndex::getTitle, q)
                    .or().like(UnitIndex::getDescription, q)
                    .or().like(UnitIndex::getBodySummary, q));
        }
        w.orderByDesc(UnitIndex::getUpdatedAt);
        List<UnitIndex> list = unitIndexMapper.selectList(w);
        fillListDisplay(list);
        return list;
    }

    public Map<String, Object> unitDetail(String kind, Long id) {
        UnitIndex unit = unitIndexMapper.selectOne(new LambdaQueryWrapper<UnitIndex>()
                .eq(UnitIndex::getKind, kind)
                .eq(UnitIndex::getRefId, id));
        if (unit == null) {
            if (KnowledgeEnums.KIND_DOCUMENT.equals(kind)) {
                Document doc = documentMapper.selectById(id);
                if (doc == null) {
                    throw new BizException(404, "单元不存在");
                }
                Map<String, Object> m = new HashMap<>();
                m.put("kind", kind);
                m.put("refId", id);
                m.put("title", doc.getTitle());
                m.put("description", doc.getSummary());
                m.put("bodySummary", "");
                m.put("summary", doc.getSummary());
                m.put("body", doc.getBody());
                m.put("status", doc.getStatus());
                m.put("categoryId", doc.getCategoryId());
                m.put("categoryPath", categoryService.pathLabel(doc.getCategoryId()));
                m.put("productName", doc.getProductName());
                m.put("lineageId", doc.getLineageId());
                m.put("versionNo", doc.getVersionNo());
                m.put("relations", List.of());
                return m;
            }
            Slice slice = sliceMapper.selectById(id);
            if (slice == null) {
                throw new BizException(404, "单元不存在");
            }
            Map<String, Object> m = new HashMap<>();
            m.put("kind", kind);
            m.put("refId", id);
            m.put("documentId", slice.getDocumentId());
            m.put("title", slice.getTitle());
            m.put("description", slice.getDescription());
            m.put("bodySummary", slice.getBodySummary());
            m.put("body", slice.getBody());
            m.put("status", slice.getStatus());
            m.put("categoryId", slice.getCategoryId());
            m.put("categoryPath", categoryService.pathLabel(slice.getCategoryId()));
            m.put("techTags", slice.getTechTags());
            m.put("versionNo", slice.getVersionNo());
            m.put("documentTitle", resolveDocumentTitle(slice.getDocumentId()));
            m.put("productName", resolveProductName(slice.getDocumentId()));
            m.put("relations", listRelations(kind, id));
            return m;
        }
        Map<String, Object> m = new HashMap<>();
        m.put("kind", unit.getKind());
        m.put("refId", unit.getRefId());
        m.put("documentId", unit.getDocumentId());
        m.put("title", unit.getTitle());
        m.put("description", unit.getDescription());
        m.put("bodySummary", unit.getBodySummary());
        if (KnowledgeEnums.KIND_DOCUMENT.equals(unit.getKind())) {
            m.put("summary", unit.getDescription());
        }
        m.put("body", unit.getBody());
        m.put("status", unit.getStatus());
        m.put("categoryId", unit.getCategoryId());
        m.put("categoryPath", categoryService.pathLabel(unit.getCategoryId()));
        m.put("techTags", unit.getTechTags());
        if (KnowledgeEnums.KIND_SLICE.equals(unit.getKind())) {
            m.put("documentTitle", resolveDocumentTitle(unit.getDocumentId()));
            m.put("productName", resolveProductName(unit.getDocumentId()));
            Slice slice = sliceMapper.selectById(unit.getRefId());
            if (slice != null) {
                m.put("versionNo", slice.getVersionNo());
            }
        } else if (KnowledgeEnums.KIND_DOCUMENT.equals(unit.getKind())) {
            Document doc = documentMapper.selectById(unit.getRefId());
            if (doc != null) {
                m.put("productName", doc.getProductName());
                m.put("lineageId", doc.getLineageId());
                m.put("versionNo", doc.getVersionNo());
            }
        }
        m.put("relations", listRelations(kind, id));
        return m;
    }

    private void fillListDisplay(List<UnitIndex> list) {
        Map<Long, Document> cache = new HashMap<>();
        for (UnitIndex u : list) {
            Long docId = null;
            if (KnowledgeEnums.KIND_SLICE.equals(u.getKind())) {
                docId = u.getDocumentId();
            } else if (KnowledgeEnums.KIND_DOCUMENT.equals(u.getKind())) {
                docId = u.getRefId();
            }
            if (docId == null) {
                continue;
            }
            Document doc = cache.computeIfAbsent(docId, documentMapper::selectById);
            if (doc == null) {
                continue;
            }
            u.setProductName(doc.getProductName());
            if (KnowledgeEnums.KIND_SLICE.equals(u.getKind())) {
                u.setDocumentTitle(doc.getTitle());
            }
        }
    }

    private String resolveDocumentTitle(Long documentId) {
        if (documentId == null) {
            return null;
        }
        Document doc = documentMapper.selectById(documentId);
        return doc == null ? null : doc.getTitle();
    }

    private String resolveProductName(Long documentId) {
        if (documentId == null) {
            return null;
        }
        Document doc = documentMapper.selectById(documentId);
        return doc == null ? null : doc.getProductName();
    }

    /**
     * 双路召回：原文（标题+简介向量）与切片（标题+摘要向量+正文 BM25），
     * WeightedRanker 融合后由千问 rerank 重排，再按 topK 截断。
     * <ul>
     *   <li>默认：按 documentId 去重，保留最高分；同分原文优先。</li>
     *   <li>仅 kinds=SLICE：不做 documentId 去重，按切片分数排序截断。</li>
     *   <li>documentIds 非空时，Milvus 侧按文章 id 精准过滤。</li>
     * </ul>
     */
    public SearchResultVo search(String q, String productName, int topK, Long categoryId, List<String> kinds) {
        return search(q, productName, topK, categoryId, kinds, null, true, null, null, null, null, false);
    }

    public SearchResultVo search(String q, String productName, int topK, Long categoryId,
                                 List<String> kinds, List<Long> documentIds) {
        return search(q, productName, topK, categoryId, kinds, documentIds, true, null, null, null, null, false);
    }

    /**
     * @param rewrite true（默认）先 LLM/规则改写再检索；false 直接用原始 q（表名等精确检索场景）
     */
    public SearchResultVo search(String q, String productName, int topK, Long categoryId,
                                 List<String> kinds, List<Long> documentIds, boolean rewrite) {
        return search(q, productName, topK, categoryId, kinds, documentIds, rewrite,
                null, null, null, null, false);
    }

    /**
     * @param titleQuery        非空时对切片 title 向量单独 embed
     * @param descriptionQuery  非空时对切片 description 向量单独 embed
     * @param bodySummaryQuery  非空时对切片 body_summary 向量单独 embed
     * @param ftsQuery          非空时作为正文 BM25；分字段模式下覆盖改写 fts
     */
    public SearchResultVo search(String q, String productName, int topK, Long categoryId,
                                 List<String> kinds, List<Long> documentIds, boolean rewrite,
                                 String titleQuery, String descriptionQuery, String bodySummaryQuery,
                                 String ftsQuery, boolean includeBody) {
        String titleQ = trimToNull(titleQuery);
        String descQ = trimToNull(descriptionQuery);
        String bodySumQ = trimToNull(bodySummaryQuery);
        String ftsOverride = trimToNull(ftsQuery);
        boolean fieldSplit = titleQ != null || descQ != null || bodySumQ != null || ftsOverride != null;

        String displayQ = StringUtils.hasText(q)
                ? q.trim()
                : firstNonBlank(bodySumQ, descQ, titleQ, ftsOverride);
        if (!StringUtils.hasText(displayQ) && !fieldSplit) {
            SearchResultVo empty = new SearchResultVo();
            empty.setQuery(q);
            empty.setTopicQuery("");
            empty.setBodyQuery("");
            empty.setFtsQuery("");
            empty.setTitleQuery("");
            empty.setDescriptionQuery("");
            empty.setBodySummaryQuery("");
            empty.setLlmRewritten(false);
            empty.setUnits(List.of());
            return empty;
        }
        if (!StringUtils.hasText(productName)) {
            throw new BizException("productName 不能为空");
        }
        if (documentIds != null && documentIds.isEmpty()) {
            SearchResultVo empty = new SearchResultVo();
            empty.setQuery(displayQ);
            empty.setTopicQuery("");
            empty.setBodyQuery("");
            empty.setFtsQuery("");
            empty.setTitleQuery(titleQ == null ? "" : titleQ);
            empty.setDescriptionQuery(descQ == null ? "" : descQ);
            empty.setBodySummaryQuery(bodySumQ == null ? "" : bodySumQ);
            empty.setLlmRewritten(false);
            empty.setUnits(List.of());
            return empty;
        }
        int limit = Math.max(1, Math.min(topK, 50));
        String product = productName.trim();

        boolean doRewrite = rewrite && !fieldSplit;
        QueryRewriteService.RewrittenQuery rewritten = doRewrite
                ? queryRewriteService.rewrite(product, displayQ)
                : QueryRewriteService.RewrittenQuery.fallback(displayQ);
        String ftsQ = fieldSplit
                ? (ftsOverride != null ? ftsOverride : "")
                : (StringUtils.hasText(rewritten.ftsQuery()) ? rewritten.ftsQuery() : rewritten.bodyQuery());

        boolean wantDoc = kinds == null || kinds.isEmpty()
                || kinds.stream().anyMatch(k -> KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(k));
        boolean wantSlice = kinds == null || kinds.isEmpty()
                || kinds.stream().anyMatch(k -> KnowledgeEnums.KIND_SLICE.equalsIgnoreCase(k));
        boolean sliceOnly = wantSlice && !wantDoc;

        MilvusSliceIndex sliceIndex = milvusSliceIndex.getIfAvailable();
        MilvusDocumentIndex docIndex = milvusDocumentIndex.getIfAvailable();
        if (sliceIndex == null || docIndex == null) {
            throw new BizException("Milvus 未启用，无法检索");
        }

        int fetch = Math.min(50, Math.max(limit * 2, limit));
        List<SearchHit> docHits = List.of();
        List<SearchHit> sliceHits = List.of();
        try {
            if (fieldSplit) {
                float[] titleVec = embedOrNull(titleQ);
                float[] descVec = embedOrNull(descQ);
                float[] bodySumVec = embedOrNull(bodySumQ);
                if (wantDoc) {
                    String docEmbedText = firstNonBlank(descQ, bodySumQ, titleQ, rewritten.topicQuery());
                    if (StringUtils.hasText(docEmbedText)) {
                        docHits = docIndex.search(
                                embeddingService.embedSearchQuery(docEmbedText),
                                product, categoryId, documentIds, fetch);
                    }
                }
                if (wantSlice) {
                    sliceHits = sliceIndex.hybridSearch(
                            titleVec, descVec, bodySumVec, ftsQ, product, categoryId, documentIds, fetch);
                }
            } else {
                float[] queryVec;
                try {
                    queryVec = embeddingService.embedSearchQuery(rewritten.topicQuery());
                } catch (Exception e) {
                    log.warn("embed query failed", e);
                    throw new BizException("向量检索失败: " + e.getMessage());
                }
                if (wantDoc) {
                    docHits = docIndex.search(queryVec, product, categoryId, documentIds, fetch);
                }
                if (wantSlice) {
                    sliceHits = sliceIndex.hybridSearch(queryVec, ftsQ, product, categoryId, documentIds, fetch);
                }
            }
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.warn("Milvus 检索失败", e);
            throw new BizException("向量检索失败: " + e.getMessage());
        }

        List<SearchHit> merged;
        if (sliceOnly) {
            merged = new ArrayList<>(sliceHits);
            merged.sort(Comparator
                    .comparing((SearchHit h) -> h.getScore() == null ? 0.0 : h.getScore()).reversed());
            for (SearchHit hit : merged) {
                Long docId = resolveDocId(hit);
                if (docId != null) {
                    hit.setDocumentId(docId);
                }
            }
        } else {
            merged = mergeByDocumentId(docHits, sliceHits, fetch);
        }
        boolean reranked = false;
        int beforeRerank = merged.size();
        if (rerankService.enabled() && beforeRerank > 1) {
            List<SearchHit> rerankedHits = rerankService.rerank(rewritten.originalQuery(), merged);
            reranked = rerankedHits != merged;
            merged = rerankedHits;
        }
        if (merged.size() > limit) {
            merged = new ArrayList<>(merged.subList(0, limit));
        }
        for (SearchHit hit : merged) {
            hit.setCategoryPath(categoryService.pathLabel(hit.getCategoryId()));
        }
        if (includeBody) {
            fillBodies(merged);
        }

        SearchResultVo vo = new SearchResultVo();
        vo.setQuery(rewritten.originalQuery());
        vo.setTopicQuery(fieldSplit
                ? firstNonBlank(bodySumQ, descQ, titleQ, rewritten.topicQuery())
                : rewritten.topicQuery());
        vo.setBodyQuery(fieldSplit ? firstNonBlank(ftsQ, rewritten.bodyQuery()) : rewritten.bodyQuery());
        vo.setFtsQuery(ftsQ);
        vo.setTitleQuery(titleQ == null ? "" : titleQ);
        vo.setDescriptionQuery(descQ == null ? "" : descQ);
        vo.setBodySummaryQuery(bodySumQ == null ? "" : bodySumQ);
        vo.setLlmRewritten(rewritten.llmRewritten());
        vo.setReranked(reranked);
        vo.setUnits(merged);
        return vo;
    }

    /**
     * 按 kind+refId 批量从 unit_index 取正文；缺索引时回退 slice/document 表。
     * 一次检索内 O(kinds) 次 IN 查询，替代调用方 N 次 GET /api/units。
     */
    void fillBodies(List<SearchHit> hits) {
        if (hits == null || hits.isEmpty()) {
            return;
        }
        Map<String, List<Long>> refIdsByKind = new HashMap<>();
        for (SearchHit hit : hits) {
            if (hit == null || hit.getRefId() == null) {
                continue;
            }
            String kind = StringUtils.hasText(hit.getKind())
                    ? hit.getKind().trim().toUpperCase()
                    : KnowledgeEnums.KIND_SLICE;
            hit.setKind(kind);
            refIdsByKind.computeIfAbsent(kind, k -> new ArrayList<>()).add(hit.getRefId());
        }
        Map<String, String> bodyByKey = new HashMap<>();
        for (Map.Entry<String, List<Long>> e : refIdsByKind.entrySet()) {
            String kind = e.getKey();
            List<Long> refIds = e.getValue().stream().distinct().toList();
            if (refIds.isEmpty()) {
                continue;
            }
            List<UnitIndex> units = unitIndexMapper.selectList(new LambdaQueryWrapper<UnitIndex>()
                    .eq(UnitIndex::getKind, kind)
                    .in(UnitIndex::getRefId, refIds));
            for (UnitIndex u : units) {
                if (u.getRefId() == null) {
                    continue;
                }
                bodyByKey.put(kind + ":" + u.getRefId(), u.getBody() == null ? "" : u.getBody());
            }
            // 索引缺失时回退主表，保证 includeBody 语义完整
            List<Long> missing = refIds.stream()
                    .filter(id -> !bodyByKey.containsKey(kind + ":" + id))
                    .toList();
            if (missing.isEmpty()) {
                continue;
            }
            if (KnowledgeEnums.KIND_SLICE.equals(kind)) {
                List<Slice> slices = sliceMapper.selectList(new LambdaQueryWrapper<Slice>()
                        .in(Slice::getId, missing));
                for (Slice s : slices) {
                    if (s.getId() == null) {
                        continue;
                    }
                    bodyByKey.put(kind + ":" + s.getId(), s.getBody() == null ? "" : s.getBody());
                }
            } else if (KnowledgeEnums.KIND_DOCUMENT.equals(kind)) {
                List<Document> docs = documentMapper.selectList(new LambdaQueryWrapper<Document>()
                        .in(Document::getId, missing));
                for (Document d : docs) {
                    if (d.getId() == null) {
                        continue;
                    }
                    bodyByKey.put(kind + ":" + d.getId(), d.getBody() == null ? "" : d.getBody());
                }
            }
        }
        for (SearchHit hit : hits) {
            if (hit == null || hit.getRefId() == null) {
                continue;
            }
            String key = hit.getKind() + ":" + hit.getRefId();
            if (bodyByKey.containsKey(key)) {
                hit.setBody(bodyByKey.get(key));
            }
        }
    }

    private float[] embedOrNull(String text) {
        if (!StringUtils.hasText(text)) {
            return null;
        }
        try {
            return embeddingService.embedSearchQuery(text.trim());
        } catch (Exception e) {
            log.warn("embed query failed text={}", text, e);
            throw new BizException("向量检索失败: " + e.getMessage());
        }
    }

    private static String trimToNull(String s) {
        if (!StringUtils.hasText(s)) {
            return null;
        }
        String t = s.trim();
        return t.isEmpty() ? null : t;
    }

    private static String firstNonBlank(String... values) {
        if (values == null) {
            return "";
        }
        for (String v : values) {
            if (StringUtils.hasText(v)) {
                return v.trim();
            }
        }
        return "";
    }

    /** 策略 A：同 documentId 保留最高分；同分 DOCUMENT 优先 */
    static List<SearchHit> mergeByDocumentId(List<SearchHit> docHits, List<SearchHit> sliceHits, int limit) {
        Map<Long, SearchHit> best = new LinkedHashMap<>();
        for (SearchHit hit : docHits) {
            Long docId = resolveDocId(hit);
            if (docId == null) {
                continue;
            }
            hit.setDocumentId(docId);
            putIfBetter(best, docId, hit);
        }
        for (SearchHit hit : sliceHits) {
            Long docId = resolveDocId(hit);
            if (docId == null) {
                continue;
            }
            hit.setDocumentId(docId);
            putIfBetter(best, docId, hit);
        }
        return best.values().stream()
                .sorted(Comparator
                        .comparing((SearchHit h) -> h.getScore() == null ? 0.0 : h.getScore()).reversed()
                        .thenComparing(h -> KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(h.getKind()) ? 0 : 1))
                .limit(limit)
                .toList();
    }

    private static Long resolveDocId(SearchHit hit) {
        if (hit.getDocumentId() != null && hit.getDocumentId() > 0) {
            return hit.getDocumentId();
        }
        if (KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(hit.getKind()) && hit.getRefId() != null) {
            return hit.getRefId();
        }
        return hit.getDocumentId();
    }

    private static void putIfBetter(Map<Long, SearchHit> best, Long docId, SearchHit candidate) {
        SearchHit existing = best.get(docId);
        if (existing == null) {
            best.put(docId, candidate);
            return;
        }
        double cs = candidate.getScore() == null ? 0.0 : candidate.getScore();
        double es = existing.getScore() == null ? 0.0 : existing.getScore();
        if (cs > es) {
            best.put(docId, candidate);
            return;
        }
        if (cs == es) {
            boolean candDoc = KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(candidate.getKind());
            boolean existDoc = KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(existing.getKind());
            if (candDoc && !existDoc) {
                best.put(docId, candidate);
            }
        }
    }

    private List<Relation> listRelations(String kind, Long id) {
        return relationMapper.selectList(new LambdaQueryWrapper<Relation>()
                .and(w -> w.eq(Relation::getFromKind, kind).eq(Relation::getFromId, id)
                        .or()
                        .eq(Relation::getToKind, kind).eq(Relation::getToId, id)));
    }
}
