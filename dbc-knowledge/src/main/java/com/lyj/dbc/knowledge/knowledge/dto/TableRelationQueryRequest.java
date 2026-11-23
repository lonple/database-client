package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

/**
 * POST /api/search/table-relations — 按一张表查图谱邻接并整理成边。
 */
@Data
public class TableRelationQueryRequest {
    private Long graphId;
    private String table;
    /** 默认 1，最大 3 */
    private Integer maxDepth;
    /** 默认 50，最大 200 */
    private Integer limit;
}
