package com.lyj.dbc.graph.query.dto;

import lombok.Data;

/**
 * POST /api/graphs/{graphId}/table-neighbors
 * <p>
 * 查询某表节点的无向邻接表，并解析每对 JOIN 列。
 */
@Data
public class TableNeighborsRequest {
    /** 中心表名（节点 name） */
    private String table;
    /** 最大跳数 1..3，默认 1 */
    private Integer maxDepth;
    /** 邻接表数量上限，默认 50 */
    private Integer limit;
}
