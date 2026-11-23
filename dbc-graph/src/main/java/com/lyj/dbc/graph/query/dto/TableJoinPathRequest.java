package com.lyj.dbc.graph.query.dto;

import lombok.Data;

/**
 * POST /api/graphs/{graphId}/table-join-path
 * <p>
 * 两张表节点之间的无向最短路径，并解析双向边为 JOIN 列对
 * （如 {@code hr_employee.id 关联 att_daily_record.emp_id}）。
 */
@Data
public class TableJoinPathRequest {
    /** 起点表名（节点 name） */
    private String fromTable;
    /** 终点表名（节点 name） */
    private String toTable;
    /** 最大跳数 1..8，默认 6 */
    private Integer maxDepth;
}
