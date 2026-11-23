package com.lyj.dbc.knowledge.knowledge.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.lyj.dbc.knowledge.common.api.BizException;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import com.lyj.dbc.knowledge.knowledge.dto.SearchResultVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationQueryRequest;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationQueryResultVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableRelationVo;
import com.lyj.dbc.knowledge.knowledge.dto.TableSearchHit;
import com.lyj.dbc.knowledge.knowledge.dto.TableSearchRequest;
import com.lyj.dbc.knowledge.knowledge.dto.TableSearchResultVo;
import com.lyj.dbc.knowledge.knowledge.mapper.SliceMapper;
import com.lyj.dbc.knowledge.knowledge.support.AdaGraphClient;
import com.lyj.dbc.knowledge.knowledge.support.TableRelationAssembler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 问数表语义找表：分字段检索 → 表名过滤 → 图谱邻接展开 → 切片标题全等补全。
 */
@Service
public class TableSearchService {
    private static final Logger log = LoggerFactory.getLogger(TableSearchService.class);

    private final SearchService searchService;
    private final SliceMapper sliceMapper;
    private final AdaGraphClient adaGraphClient;
    private final CategoryService categoryService;

    public TableSearchService(SearchService searchService,
                              SliceMapper sliceMapper,
                              AdaGraphClient adaGraphClient,
                              CategoryService categoryService) {
        this.searchService = searchService;
        this.sliceMapper = sliceMapper;
        this.adaGraphClient = adaGraphClient;
        this.categoryService = categoryService;
    }

    public TableSearchResultVo searchTables(TableSearchRequest req) {
        if (req == null) {
            throw new BizException("请求体不能为空");
        }
        String product = trimToNull(req.getProductName());
        if (product == null) {
            throw new BizException("productName 不能为空");
        }
        int topK = req.getTopK() == null ? 10 : Math.max(1, Math.min(req.getTopK(), 50));
        boolean rewrite = Boolean.TRUE.equals(req.getRewrite());
        List<Long> documentIds = req.getDocumentIds();
        Long categoryId = null;
        if (StringUtils.hasText(req.getCategoryCode())) {
            categoryId = categoryService.requireByCode(req.getCategoryCode()).getId();
        }

        String titleQ = trimToNull(req.getTitleQuery());
        String descQ = trimToNull(req.getDescriptionQuery());
        String bodySumQ = trimToNull(req.getBodySummaryQuery());
        String ftsQ = trimToNull(req.getFtsQuery());
        String displayQ = firstNonBlank(descQ, titleQ, bodySumQ, ftsQ, "");

        SearchResultVo raw = searchService.search(
                displayQ,
                product,
                topK,
                categoryId,
                List.of(KnowledgeEnums.KIND_SLICE),
                documentIds,
                rewrite,
                titleQ,
                descQ,
                bodySumQ,
                ftsQ,
                false);

        LinkedHashMap<String, TableSearchHit> byName = new LinkedHashMap<>();
        int rawHitCount = raw.getUnits() == null ? 0 : raw.getUnits().size();
        int skippedTitle = 0;
        for (SearchHit hit : raw.getUnits() == null ? List.<SearchHit>of() : raw.getUnits()) {
            if (hit == null) {
                continue;
            }
            String physical = physicalTableName(hit.getTitle());
            if (physical == null) {
                skippedTitle++;
                log.debug("search_tables 跳过无法解析为物理表名的切片 title={}", hit.getTitle());
                continue;
            }
            String key = physical.toLowerCase(Locale.ROOT);
            if (byName.containsKey(key)) {
                continue;
            }
            TableSearchHit t = new TableSearchHit();
            t.setName(physical);
            t.setTitle(hit.getTitle());
            t.setDescription(hit.getDescription());
            t.setBodySummary(hit.getBodySummary());
            t.setScore(hit.getScore());
            t.setSource("HIT");
            t.setDocumentId(hit.getDocumentId());
            t.setRefId(hit.getRefId());
            byName.put(key, t);
        }
        if (skippedTitle > 0) {
            log.warn(
                    "search_tables 有切片标题未解析为表名 rawHits={} kept={} skippedTitle={}",
                    rawHitCount,
                    byName.size(),
                    skippedTitle);
        }

        List<TableRelationVo> relations = new ArrayList<>();
        Long graphId = req.getGraphId();
        // 图谱邻接失败不得拖垮已命中的表
        if (graphId != null && graphId > 0 && !byName.isEmpty()) {
            try {
                Set<String> relatedNames = new LinkedHashSet<>();
                List<String> hitNames = byName.values().stream().map(TableSearchHit::getName).toList();
                for (String hitName : hitNames) {
                    try {
                        Map<String, Object> nb = adaGraphClient.tableNeighbors(graphId, hitName, 1, 50);
                        List<TableRelationVo> hitRels =
                                TableRelationAssembler.fromNeighbors(hitName, nb.get("neighbors"));
                        for (TableRelationVo rel : hitRels) {
                            if (rel.getToTable() != null) {
                                relatedNames.add(rel.getToTable());
                            }
                            relations.add(rel);
                        }
                    } catch (Exception e) {
                        log.warn("search_tables 邻接展开失败 table={} graphId={}", hitName, graphId, e);
                    }
                }
                if (!relatedNames.isEmpty()) {
                    Map<String, Slice> sliceByTitle = loadPublishedSlicesByTitles(documentIds, relatedNames);
                    for (String related : relatedNames) {
                        String key = related.toLowerCase(Locale.ROOT);
                        if (byName.containsKey(key)) {
                            continue;
                        }
                        Slice slice = findSliceIgnoreCase(sliceByTitle, related);
                        if (slice == null) {
                            // 切片 title 可能是 database.schema.table，邻接名是裸表名
                            slice = findSliceByPhysicalName(sliceByTitle, related);
                        }
                        if (slice == null) {
                            log.debug("邻接表无匹配切片 title={}", related);
                            continue;
                        }
                        String physical = physicalTableName(slice.getTitle());
                        TableSearchHit t = new TableSearchHit();
                        t.setName(physical != null ? physical : related);
                        t.setTitle(slice.getTitle());
                        t.setDescription(slice.getDescription());
                        t.setBodySummary(slice.getBodySummary());
                        t.setScore(null);
                        t.setSource("RELATED");
                        t.setDocumentId(slice.getDocumentId());
                        t.setRefId(slice.getId());
                        byName.put(key, t);
                    }
                }
            } catch (Exception e) {
                log.warn("search_tables 图谱邻接整段失败 graphId={}，仍返回语义命中表", graphId, e);
                relations = new ArrayList<>();
            }
        }

        TableSearchResultVo vo = new TableSearchResultVo();
        vo.setQuery(displayQ);
        vo.setTitleQuery(titleQ == null ? "" : titleQ);
        vo.setDescriptionQuery(descQ == null ? "" : descQ);
        vo.setBodySummaryQuery(bodySumQ == null ? "" : bodySumQ);
        vo.setFtsQuery(ftsQ == null ? "" : ftsQ);
        vo.setTables(new ArrayList<>(byName.values()));
        vo.setTableRelations(relations);
        return vo;
    }

    /**
     * 按一张表查图谱邻接，关联结构与 {@link #searchTables} 的 tableRelations 相同。
     */
    public TableRelationQueryResultVo listTableRelations(TableRelationQueryRequest req) {
        if (req == null) {
            throw new BizException("请求体不能为空");
        }
        if (req.getGraphId() == null || req.getGraphId() <= 0) {
            throw new BizException("graphId 不能为空");
        }
        String table = trimToNull(req.getTable());
        if (table == null) {
            throw new BizException("table 不能为空");
        }
        int maxDepth = req.getMaxDepth() == null ? 1 : Math.max(1, Math.min(req.getMaxDepth(), 3));
        int limit = req.getLimit() == null ? 50 : Math.max(1, Math.min(req.getLimit(), 200));
        Map<String, Object> nb = adaGraphClient.tableNeighbors(req.getGraphId(), table, maxDepth, limit);
        TableRelationQueryResultVo vo = new TableRelationQueryResultVo();
        vo.setGraphId(req.getGraphId());
        vo.setTable(table);
        vo.setTableRelations(TableRelationAssembler.fromNeighbors(table, nb.get("neighbors")));
        return vo;
    }

    private Map<String, Slice> loadPublishedSlicesByTitles(List<Long> documentIds, Set<String> titles) {
        if (titles == null || titles.isEmpty()) {
            return Map.of();
        }
        List<String> titleList = new ArrayList<>(titles);
        LambdaQueryWrapper<Slice> w = new LambdaQueryWrapper<>();
        w.eq(Slice::getStatus, KnowledgeEnums.STATUS_PUBLISHED);
        if (documentIds != null && !documentIds.isEmpty()) {
            w.in(Slice::getDocumentId, documentIds);
        }
        // 裸表名或 database.schema.table：等值，或以 .表名 结尾
        w.and(q -> {
            for (int i = 0; i < titleList.size(); i++) {
                String t = titleList.get(i);
                if (i == 0) {
                    q.apply("LOWER(title) = LOWER({0})", t)
                            .or()
                            .apply("LOWER(title) LIKE LOWER({0})", "%." + t);
                } else {
                    q.or().apply("LOWER(title) = LOWER({0})", t)
                            .or()
                            .apply("LOWER(title) LIKE LOWER({0})", "%." + t);
                }
            }
        });
        List<Slice> slices = sliceMapper.selectList(w);
        Map<String, Slice> out = new HashMap<>();
        for (Slice s : slices) {
            if (s == null || !StringUtils.hasText(s.getTitle())) {
                continue;
            }
            out.putIfAbsent(s.getTitle().toLowerCase(Locale.ROOT), s);
            String physical = physicalTableName(s.getTitle());
            if (physical != null) {
                out.putIfAbsent(physical.toLowerCase(Locale.ROOT), s);
            }
        }
        return out;
    }

    private static Slice findSliceIgnoreCase(Map<String, Slice> byLowerTitle, String name) {
        if (byLowerTitle == null || !StringUtils.hasText(name)) {
            return null;
        }
        return byLowerTitle.get(name.toLowerCase(Locale.ROOT));
    }

    /** 切片 title 为 database.schema.table 时，按物理表名（最后一段）匹配。 */
    private static Slice findSliceByPhysicalName(Map<String, Slice> byLowerTitle, String physicalName) {
        if (byLowerTitle == null || !StringUtils.hasText(physicalName)) {
            return null;
        }
        String want = physicalName.toLowerCase(Locale.ROOT);
        for (Map.Entry<String, Slice> e : byLowerTitle.entrySet()) {
            String physical = physicalTableName(e.getKey());
            if (want.equals(physical != null ? physical.toLowerCase(Locale.ROOT) : null)) {
                return e.getValue();
            }
        }
        return null;
    }

    /**
     * 从切片标题抽出物理表名。元数据切片标题常为 {@code database.schema.table}（三段），
     * 也兼容 {@code schema.table} / {@code table}。图谱节点与问数选表用最后一段表名。
     */
    static String physicalTableName(String raw) {
        if (!StringUtils.hasText(raw)) {
            return null;
        }
        String s = raw.trim();
        if (s.length() > 128) {
            return null;
        }
        s = s.replace("\"", "").replace("`", "");
        String[] parts = s.split("\\.");
        // 问数入库标题：database.schema.table（3 段）；旧规则只认 1～2 段会把命中全部滤掉
        if (parts.length < 1 || parts.length > 3) {
            return null;
        }
        for (String p : parts) {
            if (!StringUtils.hasText(p)) {
                return null;
            }
            char c0 = p.charAt(0);
            if (c0 > 127 || Character.isDigit(c0)) {
                return null;
            }
            for (int i = 0; i < p.length(); i++) {
                char c = p.charAt(i);
                if (c > 127 || !(Character.isLetterOrDigit(c) || c == '_')) {
                    return null;
                }
            }
        }
        return parts[parts.length - 1];
    }

    private static String trimToNull(String s) {
        if (!StringUtils.hasText(s)) {
            return null;
        }
        String t = s.trim();
        return t.isEmpty() ? null : t;
    }

    private static String firstNonBlank(String... values) {
        for (String v : values) {
            if (StringUtils.hasText(v)) {
                return v.trim();
            }
        }
        return "";
    }
}
