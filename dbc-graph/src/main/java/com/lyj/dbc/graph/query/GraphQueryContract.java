package com.lyj.dbc.graph.query;

/**
 * 图谱关系查询契约：HTTP / 助手 / MCP {@code query_graph_relations} 共用。
 * 边只有业务类型（如 父母、配偶），祖孙等称谓由「父母」方向 + 节点一级属性 gender 解读。
 */
public final class GraphQueryContract {
    private GraphQueryContract() {
    }

    public static final String TOOL_NAME = "query_graph_relations";

    /**
     * {@code @Tool(description=...)} 文案；参数 schema 由 {@code @ToolParam} 从方法签名生成，
     * 不要再手写 JSON Schema，也不要塞进 system 提示词。
     */
    public static final String ASSISTANT_TOOL_DESCRIPTION = """
            查询当前知识图谱中的实体关系。边类型只有业务值如「父母」「配偶」，没有「爷爷」「父亲」边。
            人物性别为节点一级属性 gender（男/女）。「父母」边有向：长辈→子女；起点男=父亲、女=母亲。
            用法：
            - 两人啥关系：mode=BETWEEN，nodeName 与 toNodeName 各一方姓名；可选 relTypes；解读 path/hops + gender。
            - 某人父母：mode=NEIGHBORS，relTypes=父母，direction=IN，maxDepth=1。
            - 某人子女：同上 direction=OUT。
            - 爷爷/奶奶等：NEIGHBORS + 父母 + IN + maxDepth=2，再按 gender 解读（勿在不知终点时用 PATH）。
            - 配偶：relTypes=配偶，direction=BOTH。
            maxDepth 范围 1..6。报错时改参数再调，不要把 error 原文当最终答案。
            """;

    /** 工具报错 hint / HTTP guide，非助手 system 正文。 */
    public static final String GUIDE = ASSISTANT_TOOL_DESCRIPTION;

    public static final String PATH_ERROR =
            "PATH 需要同时提供起点 nodeName 与终点 toNodeName（有向）。"
                    + "问两人啥关系请用 BETWEEN（无向最短路）。查爷爷/父母用 NEIGHBORS。";

    public static final String BETWEEN_ERROR =
            "BETWEEN（两人关系）需要 nodeName 与 toNodeName。"
                    + "返回无向有界最短路径；用 hops + nodes[].gender 解读称谓。";

    public static final String NEIGHBORS_ERROR =
            "NEIGHBORS/SUBGRAPH 需要 nodeName 或 nodeId。"
                    + "查父母/祖辈：relTypes=[父母]，direction=IN；查子女：direction=OUT。角色看节点 gender。";

    public static final String REL_TYPE_ERROR =
            "BY_REL_TYPE 需要 relTypes（如 父母、配偶）。图中无「爷爷」边类型。";

    public static final String MCP_TOOL_DESCRIPTION =
            "Query relations in one knowledge graph (graphId from list_graphs). "
                    + "Edges are business relTypes only (e.g. 父母, 配偶). "
                    + "Person gender is first-class node field gender (男/女). "
                    + "mode: NEIGHBORS|PATH|BETWEEN|BY_REL_TYPE|SUBGRAPH. "
                    + "For 'what is the relation between A and B': mode=BETWEEN, nodeName=A, toNodeName=B, "
                    + "optional relTypes=父母,配偶, maxDepth<=6; interpret path/hops with gender. "
                    + "For 爷爷/父母 without knowing the other name: NEIGHBORS IN maxDepth=2.";
}
