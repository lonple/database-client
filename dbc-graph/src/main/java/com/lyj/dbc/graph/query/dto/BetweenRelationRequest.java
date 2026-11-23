package com.lyj.dbc.graph.query.dto;

import lombok.Data;

import java.util.List;

/** POST /api/graphs/{graphId}/relations/between */
@Data
public class BetweenRelationRequest {
    /** 一方姓名 */
    private String fromName;
    /** 另一方姓名 */
    private String toName;
    /** 可选：只走这些边类型，如 ["父母","配偶"] */
    private List<String> relTypes;
    /** 最大跳数 1..6，默认 6 */
    private Integer maxDepth;
}
