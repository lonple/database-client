package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

@Data
public class TableSearchHit {
    /** 物理表名（通常等于 title） */
    private String name;
    private String title;
    private String description;
    private String bodySummary;
    private Double score;
    /** HIT=语义命中；RELATED=图谱邻接补全 */
    private String source;
    private Long documentId;
    private Long refId;
}
