package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;

@Data
public class SearchHit {
    private Long id;
    private String kind;
    private Long refId;
    private Long documentId;
    private String title;
    /** DOCUMENT=原文简介；SLICE=切片说明 */
    private String description;
    /** SLICE=正文摘要 */
    private String bodySummary;
    /** includeBody=true 时由检索接口批量填充；默认不返回以控制载荷 */
    private String body;
    private Long categoryId;
    private String status;
    private List<String> techTags;
    private Double score;
    private String categoryPath;
}
