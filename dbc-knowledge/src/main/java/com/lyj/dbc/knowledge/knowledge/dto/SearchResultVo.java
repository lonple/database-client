package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;

@Data
public class SearchResultVo {
    private String query;
    private String topicQuery;
    private String bodyQuery;
    private String ftsQuery;
    /** 分字段检索：打 embedding_title */
    private String titleQuery;
    /** 分字段检索：打 embedding_description */
    private String descriptionQuery;
    /** 分字段检索：打 embedding_body_summary */
    private String bodySummaryQuery;
    private boolean llmRewritten;
    /** 是否已用千问 rerank 重排（失败则 false，units 仍为加权融合顺序） */
    private boolean reranked;
    private List<SearchHit> units;
}
