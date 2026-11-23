package com.lyj.dbc.graph.query.dto;

import lombok.Data;

import java.util.List;

/**
 * POST /api/graphs/{graphId}/query 请求体（MCP query_graph_relations / 助手 args 同形）。
 * <p>
 * 边只有业务类型（父母、配偶等），没有「爷爷」「父亲」边。
 * 人物角色用「父母」边方向（长辈→子女）+ 节点 {@code props.gender}（男/女）解读。
 */
@Data
public class GraphQueryRequest {
    /**
     * NEIGHBORS | PATH | BETWEEN | BY_REL_TYPE | SUBGRAPH。
     * 问「两人啥关系」用 BETWEEN（无向最短路）；PATH 仍为有向。
     */
    private String mode;
    /** 起点姓名。查「王小雨的爷爷」时填王小雨，不要填未知的祖父名。BETWEEN 时为一方姓名。 */
    private String nodeName;
    private String nodeId;
    /** PATH / BETWEEN：另一方姓名。 */
    private String toNodeName;
    /** 边类型，如 ["父母"]、["配偶"]。不要传「爷爷」。 */
    private List<String> relTypes;
    /**
     * OUT=沿边方向（父母：查子女）；IN=逆边（父母：查父母/祖辈）；BOTH。
     * 默认 OUT。
     */
    private String direction;
    /** 祖辈称谓建议 2（子女→父→祖父）。范围 1..6。 */
    private Integer maxDepth;
    private Integer limit;
}
