package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;

/**
 * POST /api/search/tables — 问数表语义找表。
 */
@Data
public class TableSearchRequest {
    private String productName;
    /** 按分类编码检索，问数不再传 documentIds。 */
    private String categoryCode;
    private List<Long> documentIds;
    private Integer topK;
    /** 表英文 → 切片标题向量 */
    private String titleQuery;
    /** 表中文 → 切片说明向量 */
    private String descriptionQuery;
    /** 字段对 → 正文摘要向量 */
    private String bodySummaryQuery;
    /** 表对|字段对 → 正文 BM25 */
    private String ftsQuery;
    /** 可选：库表关系图谱 id，有值则展开邻接表 */
    private Long graphId;
    private Boolean rewrite;
}
