package com.lyj.dbc.graph.neo4j;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.graph.canvas.dto.EdgeVo;
import com.lyj.dbc.graph.canvas.dto.NodeVo;
import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.query.GraphQueryContract;
import org.neo4j.driver.Driver;
import org.neo4j.driver.Record;
import org.neo4j.driver.Result;
import org.neo4j.driver.Session;
import org.neo4j.driver.Values;
import org.neo4j.driver.types.Node;
import org.neo4j.driver.types.Relationship;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component
public class Neo4jGateway {
    private final Driver driver;
    private final ObjectMapper mapper;

    public Neo4jGateway(Driver driver, ObjectMapper mapper) {
        this.driver = driver;
        this.mapper = mapper;
    }

    public List<NodeVo> listNodes(long graphId) {
        try (Session session = driver.session()) {
            Result result = session.run(
                    "MATCH (n:KgNode {graphId:$graphId}) RETURN n ORDER BY n.name",
                    Values.parameters("graphId", graphId));
            List<NodeVo> list = new ArrayList<>();
            while (result.hasNext()) {
                list.add(toNodeVo(result.next().get("n").asNode()));
            }
            return list;
        }
    }

    public List<EdgeVo> listEdges(long graphId) {
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (a:KgNode {graphId:$graphId})-[r:KgRel {graphId:$graphId}]->(b:KgNode {graphId:$graphId})
                    RETURN r, a.nodeId AS fromId, b.nodeId AS toId
                    """, Values.parameters("graphId", graphId));
            List<EdgeVo> list = new ArrayList<>();
            while (result.hasNext()) {
                Record rec = result.next();
                list.add(toEdgeVo(rec.get("r").asRelationship(),
                        rec.get("fromId").asString(),
                        rec.get("toId").asString()));
            }
            return list;
        }
    }

    public NodeVo createNode(long graphId, String name, String nodeType, String description,
                             Map<String, Object> props, String refKind, Long refId, Double x, Double y) {
        return createNode(graphId, name, nodeType, description, null, props, refKind, refId, x, y);
    }

    public NodeVo createNode(long graphId, String name, String nodeType, String description,
                             String gender, Map<String, Object> props, String refKind, Long refId,
                             Double x, Double y) {
        String nodeId = UUID.randomUUID().toString();
        String resolvedGender = resolveGender(gender, props);
        Map<String, Object> storeProps = stripGenderFromProps(props);
        String propsJson = toPropsJson(storeProps);
        try (Session session = driver.session()) {
            Record rec = session.run("""
                    CREATE (n:KgNode {
                      graphId:$graphId, nodeId:$nodeId, name:$name,
                      nodeType:$nodeType, description:$description,
                      gender:$gender,
                      propsJson:$propsJson, refKind:$refKind, refId:$refId,
                      x:$x, y:$y
                    })
                    RETURN n
                    """, Values.parameters(
                    "graphId", graphId,
                    "nodeId", nodeId,
                    "name", name,
                    "nodeType", nullToEmpty(nodeType),
                    "description", nullToEmpty(description),
                    "gender", resolvedGender,
                    "propsJson", propsJson,
                    "refKind", refKind,
                    "refId", refId,
                    "x", x == null ? 100d : x,
                    "y", y == null ? 100d : y
            )).single();
            return toNodeVo(rec.get("n").asNode());
        }
    }

    public NodeVo updateNode(long graphId, String nodeId, String name, String nodeType, String description,
                             Map<String, Object> props, String refKind, Long refId) {
        return updateNode(graphId, nodeId, name, nodeType, description, null, props, refKind, refId);
    }

    /**
     * @param gender 非 null 时更新一级属性（空串清空）；null 表示不改，除非 props 里带了 gender
     */
    public NodeVo updateNode(long graphId, String nodeId, String name, String nodeType, String description,
                             String gender, Map<String, Object> props, String refKind, Long refId) {
        try (Session session = driver.session()) {
            Map<String, Object> params = new HashMap<>();
            params.put("graphId", graphId);
            params.put("nodeId", nodeId);
            StringBuilder set = new StringBuilder("n.updatedAt = timestamp()");
            if (name != null) {
                set.append(", n.name = $name");
                params.put("name", name);
            }
            if (nodeType != null) {
                set.append(", n.nodeType = $nodeType");
                params.put("nodeType", nodeType);
            }
            if (description != null) {
                set.append(", n.description = $description");
                params.put("description", description);
            }
            String genderFromProps = null;
            if (props != null) {
                genderFromProps = extractGenderString(props);
                set.append(", n.propsJson = $propsJson");
                params.put("propsJson", toPropsJson(stripGenderFromProps(props)));
            }
            if (gender != null) {
                set.append(", n.gender = $gender");
                params.put("gender", blankToNull(gender));
            } else if (genderFromProps != null) {
                set.append(", n.gender = $gender");
                params.put("gender", genderFromProps);
            }
            if (refKind != null) {
                set.append(", n.refKind = $refKind");
                params.put("refKind", refKind.isBlank() ? null : refKind);
            }
            if (refId != null) {
                set.append(", n.refId = $refId");
                params.put("refId", refId);
            }
            Result result = session.run(
                    "MATCH (n:KgNode {graphId:$graphId, nodeId:$nodeId}) SET " + set + " RETURN n",
                    params);
            if (!result.hasNext()) {
                throw new BizException(404, "节点不存在: " + nodeId);
            }
            return toNodeVo(result.next().get("n").asNode());
        }
    }

    /** 将 propsJson 中的 gender 提升为节点一级属性（幂等，供启动或运维调用）。 */
    public int migrateGenderFromProps() {
        int updated = 0;
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (n:KgNode)
                    WHERE n.gender IS NULL AND n.propsJson CONTAINS 'gender'
                    RETURN n.nodeId AS nodeId, n.graphId AS graphId, n.propsJson AS propsJson
                    """);
            while (result.hasNext()) {
                Record rec = result.next();
                Map<String, Object> props = parseProps(rec.get("propsJson").asString("{}"));
                String g = extractGenderString(props);
                if (g == null) {
                    continue;
                }
                session.run("""
                        MATCH (n:KgNode {graphId:$graphId, nodeId:$nodeId})
                        SET n.gender = $gender, n.propsJson = $propsJson
                        """, Values.parameters(
                        "graphId", rec.get("graphId").asLong(),
                        "nodeId", rec.get("nodeId").asString(),
                        "gender", g,
                        "propsJson", toPropsJson(stripGenderFromProps(props))
                ));
                updated++;
            }
        }
        return updated;
    }

    public void updatePosition(long graphId, String nodeId, double x, double y) {
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (n:KgNode {graphId:$graphId, nodeId:$nodeId})
                    SET n.x = $x, n.y = $y
                    RETURN n.nodeId AS id
                    """, Values.parameters("graphId", graphId, "nodeId", nodeId, "x", x, "y", y));
            if (!result.hasNext()) {
                throw new BizException(404, "节点不存在: " + nodeId);
            }
        }
    }

    public void deleteNode(long graphId, String nodeId) {
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (n:KgNode {graphId:$graphId, nodeId:$nodeId})
                    DETACH DELETE n
                    RETURN count(*) AS c
                    """, Values.parameters("graphId", graphId, "nodeId", nodeId));
            long c = result.single().get("c").asLong();
            if (c == 0) {
                throw new BizException(404, "节点不存在: " + nodeId);
            }
        }
    }

    public EdgeVo createEdge(long graphId, String fromNodeId, String toNodeId, String relType, String description) {
        if (!StringUtils.hasText(relType)) {
            throw new BizException("关系类型不能为空");
        }
        String edgeId = UUID.randomUUID().toString();
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (a:KgNode {graphId:$graphId, nodeId:$fromId})
                    MATCH (b:KgNode {graphId:$graphId, nodeId:$toId})
                    CREATE (a)-[r:KgRel {
                      graphId:$graphId, edgeId:$edgeId,
                      relType:$relType, description:$description
                    }]->(b)
                    RETURN r, a.nodeId AS fromId, b.nodeId AS toId
                    """, Values.parameters(
                    "graphId", graphId,
                    "fromId", fromNodeId,
                    "toId", toNodeId,
                    "edgeId", edgeId,
                    "relType", relType.trim(),
                    "description", nullToEmpty(description)
            ));
            if (!result.hasNext()) {
                throw new BizException(404, "端点节点不存在");
            }
            Record rec = result.next();
            return toEdgeVo(rec.get("r").asRelationship(),
                    rec.get("fromId").asString(),
                    rec.get("toId").asString());
        }
    }

    /**
     * 批量建节点。每行需含 nodeId/name/nodeType/description/propsJson/x/y，可选 gender/refKind/refId。
     */
    public int bulkCreateNodes(long graphId, List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return 0;
        }
        try (Session session = driver.session()) {
            Result result = session.run("""
                    UNWIND $rows AS row
                    CREATE (n:KgNode {
                      graphId:$graphId, nodeId:row.nodeId, name:row.name,
                      nodeType:coalesce(row.nodeType, ''),
                      description:coalesce(row.description, ''),
                      gender:row.gender,
                      propsJson:coalesce(row.propsJson, '{}'),
                      refKind:row.refKind, refId:row.refId,
                      x:coalesce(row.x, 100.0), y:coalesce(row.y, 100.0)
                    })
                    RETURN count(n) AS c
                    """, Values.parameters("graphId", graphId, "rows", rows));
            return (int) result.single().get("c").asLong();
        }
    }

    /**
     * 批量建边。每行需含 edgeId/fromId/toId/relType，可选 description。
     */
    public int bulkCreateEdges(long graphId, List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return 0;
        }
        try (Session session = driver.session()) {
            Result result = session.run("""
                    UNWIND $rows AS row
                    MATCH (a:KgNode {graphId:$graphId, nodeId:row.fromId})
                    MATCH (b:KgNode {graphId:$graphId, nodeId:row.toId})
                    CREATE (a)-[r:KgRel {
                      graphId:$graphId, edgeId:row.edgeId,
                      relType:row.relType,
                      description:coalesce(row.description, '')
                    }]->(b)
                    RETURN count(r) AS c
                    """, Values.parameters("graphId", graphId, "rows", rows));
            return (int) result.single().get("c").asLong();
        }
    }

    public EdgeVo updateEdge(long graphId, String edgeId, String relType, String description) {
        try (Session session = driver.session()) {
            Map<String, Object> params = new HashMap<>();
            params.put("graphId", graphId);
            params.put("edgeId", edgeId);
            StringBuilder set = new StringBuilder("r.updatedAt = timestamp()");
            if (relType != null) {
                if (!StringUtils.hasText(relType)) {
                    throw new BizException("关系类型不能为空");
                }
                set.append(", r.relType = $relType");
                params.put("relType", relType.trim());
            }
            if (description != null) {
                set.append(", r.description = $description");
                params.put("description", description);
            }
            Result result = session.run("""
                    MATCH (a:KgNode {graphId:$graphId})-[r:KgRel {graphId:$graphId, edgeId:$edgeId}]->(b:KgNode {graphId:$graphId})
                    SET %s
                    RETURN r, a.nodeId AS fromId, b.nodeId AS toId
                    """.formatted(set), params);
            if (!result.hasNext()) {
                throw new BizException(404, "边不存在: " + edgeId);
            }
            Record rec = result.next();
            return toEdgeVo(rec.get("r").asRelationship(),
                    rec.get("fromId").asString(),
                    rec.get("toId").asString());
        }
    }

    public void deleteEdge(long graphId, String edgeId) {
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH ()-[r:KgRel {graphId:$graphId, edgeId:$edgeId}]->()
                    DELETE r
                    RETURN count(*) AS c
                    """, Values.parameters("graphId", graphId, "edgeId", edgeId));
            if (result.single().get("c").asLong() == 0) {
                throw new BizException(404, "边不存在: " + edgeId);
            }
        }
    }

    public void deleteGraphData(long graphId) {
        try (Session session = driver.session()) {
            session.run("MATCH (n:KgNode {graphId:$graphId}) DETACH DELETE n",
                    Values.parameters("graphId", graphId));
        }
    }

    public Map<String, Object> query(long graphId, String mode, String nodeName, String nodeId,
                                     String toNodeName, List<String> relTypes, String direction,
                                     int maxDepth, int limit) {
        String m = mode == null ? "NEIGHBORS" : mode.trim().toUpperCase();
        return switch (m) {
            case "NEIGHBORS" -> queryNeighbors(graphId, nodeName, nodeId, relTypes, direction, maxDepth, limit);
            case "PATH" -> queryPath(graphId, nodeName, toNodeName, maxDepth, limit);
            case "BETWEEN" -> queryBetween(graphId, nodeName, toNodeName, relTypes, maxDepth);
            case "BY_REL_TYPE" -> queryByRelType(graphId, relTypes, limit);
            case "SUBGRAPH" -> querySubgraph(graphId, nodeName, nodeId, maxDepth, limit);
            default -> throw new BizException("不支持的查询 mode: " + mode);
        };
    }

    private Map<String, Object> queryNeighbors(long graphId, String nodeName, String nodeId,
                                               List<String> relTypes, String direction,
                                               int maxDepth, int limit) {
        String dir = direction == null ? "OUT" : direction.trim().toUpperCase();
        String pattern = switch (dir) {
            case "IN" -> "(n)<-[r:KgRel*1..%d]-(m)".formatted(maxDepth);
            case "BOTH" -> "(n)-[r:KgRel*1..%d]-(m)".formatted(maxDepth);
            default -> "(n)-[r:KgRel*1..%d]->(m)".formatted(maxDepth);
        };
        String cypher = """
                MATCH (n:KgNode {graphId:$graphId})
                WHERE ($nodeId IS NOT NULL AND n.nodeId = $nodeId)
                   OR ($nodeName IS NOT NULL AND n.name = $nodeName)
                MATCH %s
                WHERE all(rel IN r WHERE rel.graphId = $graphId)
                  AND ($relTypes IS NULL OR size($relTypes)=0 OR all(rel IN r WHERE rel.relType IN $relTypes))
                  AND m.graphId = $graphId
                RETURN n, r, m
                LIMIT $limit
                """.formatted(pattern);
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Values.parameters(
                    "graphId", graphId,
                    "nodeId", blankToNull(nodeId),
                    "nodeName", blankToNull(nodeName),
                    "relTypes", relTypes,
                    "limit", limit
            ));
            return collectPathLike(result, limit);
        }
    }

    private Map<String, Object> queryPath(long graphId, String fromName, String toName, int maxDepth, int limit) {
        if (!StringUtils.hasText(fromName) || !StringUtils.hasText(toName)) {
            throw new BizException(GraphQueryContract.PATH_ERROR);
        }
        String cypher = """
                MATCH (a:KgNode {graphId:$graphId, name:$fromName})
                MATCH (b:KgNode {graphId:$graphId, name:$toName})
                MATCH p = (a)-[:KgRel*1..%d]->(b)
                WHERE all(r IN relationships(p) WHERE r.graphId = $graphId)
                RETURN p
                ORDER BY length(p) ASC
                LIMIT $limit
                """.formatted(maxDepth);
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Values.parameters(
                    "graphId", graphId,
                    "fromName", fromName,
                    "toName", toName,
                    "limit", Math.max(1, Math.min(limit, 20))
            ));
            Map<String, NodeVo> nodes = new LinkedHashMap<>();
            Map<String, EdgeVo> edges = new LinkedHashMap<>();
            while (result.hasNext()) {
                collectDirectedPath(result.next().get("p").asPath(), nodes, edges);
            }
            return pack(nodes, edges, false);
        }
    }

    /**
     * 两节点无向最短路径（问「啥关系」）。有界，默认 maxDepth=6。
     * 可选 relTypes；返回 path（有序节点）与 hops（边及真实方向 / 沿路径方向）。
     */
    /**
     * 表关系图谱：两表无向最短路径 + 每跳双向边解析为 JOIN 列对。
     * 约定：父表 -[parentCol]-> 子表、子表 -[childCol]-> 父表；
     * 沿路径方向取 fromCol=起点→终点边的 relType，toCol=反向边 relType。
     */
    public Map<String, Object> queryTableJoinPath(long graphId, String fromTable, String toTable, int maxDepth) {
        if (!StringUtils.hasText(fromTable) || !StringUtils.hasText(toTable)) {
            throw new BizException("table-join-path 需要 fromTable 与 toTable");
        }
        String from = fromTable.trim();
        String to = toTable.trim();
        if (from.equals(to)) {
            throw new BizException("两端不能是同一张表");
        }
        int depth = Math.max(1, Math.min(maxDepth, 8));
        String cypher = """
                MATCH (a:KgNode {graphId:$graphId, name:$fromName})
                MATCH (b:KgNode {graphId:$graphId, name:$toName})
                MATCH p = shortestPath((a)-[:KgRel*1..%d]-(b))
                WHERE all(r IN relationships(p) WHERE r.graphId = $graphId)
                RETURN p
                """.formatted(depth);
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Values.parameters(
                    "graphId", graphId,
                    "fromName", from,
                    "toName", to));
            if (!result.hasNext()) {
                return emptyTableJoinPath(from, to);
            }
            org.neo4j.driver.types.Path path = result.next().get("p").asPath();
            List<String> tablePath = new ArrayList<>();
            List<String> orderedNodeIds = new ArrayList<>();
            Map<String, String> idToName = new LinkedHashMap<>();
            for (Node n : path.nodes()) {
                NodeVo vo = toNodeVo(n);
                tablePath.add(vo.getName());
                orderedNodeIds.add(vo.getNodeId());
                idToName.put(vo.getNodeId(), vo.getName());
            }
            List<Map<String, Object>> joins = new ArrayList<>();
            List<String> joinTexts = new ArrayList<>();
            for (int i = 0; i < orderedNodeIds.size() - 1; i++) {
                String leftId = orderedNodeIds.get(i);
                String rightId = orderedNodeIds.get(i + 1);
                String leftTable = idToName.get(leftId);
                String rightTable = idToName.get(rightId);
                Record cols = session.run("""
                        MATCH (l:KgNode {graphId:$graphId, nodeId:$leftId})
                        MATCH (r:KgNode {graphId:$graphId, nodeId:$rightId})
                        OPTIONAL MATCH (l)-[lr:KgRel {graphId:$graphId}]->(r)
                        OPTIONAL MATCH (r)-[rl:KgRel {graphId:$graphId}]->(l)
                        RETURN lr.relType AS leftCol, rl.relType AS rightCol,
                               lr.description AS descLr, rl.description AS descRl
                        LIMIT 1
                        """, Values.parameters(
                        "graphId", graphId,
                        "leftId", leftId,
                        "rightId", rightId)).single();
                String leftCol = cols.get("leftCol").isNull() ? null : cols.get("leftCol").asString(null);
                String rightCol = cols.get("rightCol").isNull() ? null : cols.get("rightCol").asString(null);
                if (!StringUtils.hasText(leftCol) || !StringUtils.hasText(rightCol)) {
                    // 退化：仅有单向边时用 description「a.x ↔ b.y」解析
                    String desc = !cols.get("descLr").isNull()
                            ? cols.get("descLr").asString("")
                            : (!cols.get("descRl").isNull() ? cols.get("descRl").asString("") : "");
                    String[] parsed = parseJoinDescription(desc, leftTable, rightTable);
                    if (parsed != null) {
                        leftCol = parsed[0];
                        rightCol = parsed[1];
                    }
                }
                if (!StringUtils.hasText(leftCol) || !StringUtils.hasText(rightCol)) {
                    throw new BizException("无法解析表关联列: " + leftTable + " ↔ " + rightTable);
                }
                String text = leftTable + "." + leftCol + " 关联 " + rightTable + "." + rightCol;
                Map<String, Object> join = new LinkedHashMap<>();
                join.put("leftTable", leftTable);
                join.put("leftColumn", leftCol);
                join.put("rightTable", rightTable);
                join.put("rightColumn", rightCol);
                join.put("left", leftTable + "." + leftCol);
                join.put("right", rightTable + "." + rightCol);
                join.put("text", text);
                joins.add(join);
                joinTexts.add(text);
            }
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("connected", true);
            out.put("fromTable", from);
            out.put("toTable", to);
            out.put("pathLength", joins.size());
            out.put("path", tablePath);
            out.put("joins", joins);
            out.put("joinTexts", joinTexts);
            return out;
        }
    }

    /**
     * 表关系图谱：某表的无向 1 跳邻接表，并解析每对 JOIN 列。
     * 返回 {@code table} + {@code neighbors[{table, joins, joinTexts}]}。
     */
    public Map<String, Object> queryTableNeighbors(long graphId, String table, int maxDepth, int limit) {
        if (!StringUtils.hasText(table)) {
            throw new BizException("table-neighbors 需要 table");
        }
        String center = table.trim();
        int depth = Math.max(1, Math.min(maxDepth, 3));
        int lim = Math.max(1, Math.min(limit, 200));
        String cypher = """
                MATCH (a:KgNode {graphId:$graphId, name:$table})
                MATCH (a)-[:KgRel*1..%d]-(b:KgNode {graphId:$graphId})
                WHERE a <> b
                RETURN DISTINCT b.name AS neighborName, b.nodeId AS neighborId
                LIMIT $limit
                """.formatted(depth);
        try (Session session = driver.session()) {
            Result result = session.run(cypher, Values.parameters(
                    "graphId", graphId,
                    "table", center,
                    "limit", lim));
            List<Map<String, Object>> neighbors = new ArrayList<>();
            while (result.hasNext()) {
                Record rec = result.next();
                String neighbor = rec.get("neighborName").asString(null);
                if (!StringUtils.hasText(neighbor) || neighbor.equals(center)) {
                    continue;
                }
                Map<String, Object> joinPair = resolveDirectJoin(session, graphId, center, neighbor);
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("table", neighbor);
                item.put("joins", joinPair.get("joins"));
                item.put("joinTexts", joinPair.get("joinTexts"));
                neighbors.add(item);
            }
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("table", center);
            out.put("neighbors", neighbors);
            return out;
        }
    }

    /**
     * 解析两表之间的直接（1 跳）JOIN 列；无法解析时 joins/joinTexts 为空列表（不抛错）。
     */
    private Map<String, Object> resolveDirectJoin(Session session, long graphId, String leftTable, String rightTable) {
        List<Map<String, Object>> joins = new ArrayList<>();
        List<String> joinTexts = new ArrayList<>();
        Result joinResult = session.run("""
                MATCH (l:KgNode {graphId:$graphId, name:$leftName})
                MATCH (r:KgNode {graphId:$graphId, name:$rightName})
                OPTIONAL MATCH (l)-[lr:KgRel {graphId:$graphId}]->(r)
                OPTIONAL MATCH (r)-[rl:KgRel {graphId:$graphId}]->(l)
                RETURN lr.relType AS leftCol, rl.relType AS rightCol,
                       lr.description AS descLr, rl.description AS descRl
                LIMIT 1
                """, Values.parameters(
                "graphId", graphId,
                "leftName", leftTable,
                "rightName", rightTable));
        if (joinResult.hasNext()) {
            Record cols = joinResult.next();
            String leftCol = cols.get("leftCol").isNull() ? null : cols.get("leftCol").asString(null);
            String rightCol = cols.get("rightCol").isNull() ? null : cols.get("rightCol").asString(null);
            if (!StringUtils.hasText(leftCol) || !StringUtils.hasText(rightCol)) {
                String desc = !cols.get("descLr").isNull()
                        ? cols.get("descLr").asString("")
                        : (!cols.get("descRl").isNull() ? cols.get("descRl").asString("") : "");
                String[] parsed = parseJoinDescription(desc, leftTable, rightTable);
                if (parsed != null) {
                    leftCol = parsed[0];
                    rightCol = parsed[1];
                }
            }
            if (StringUtils.hasText(leftCol) && StringUtils.hasText(rightCol)) {
                String text = leftTable + "." + leftCol + " 关联 " + rightTable + "." + rightCol;
                Map<String, Object> join = new LinkedHashMap<>();
                join.put("leftTable", leftTable);
                join.put("leftColumn", leftCol);
                join.put("rightTable", rightTable);
                join.put("rightColumn", rightCol);
                join.put("left", leftTable + "." + leftCol);
                join.put("right", rightTable + "." + rightCol);
                join.put("text", text);
                joins.add(join);
                joinTexts.add(text);
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("joins", joins);
        out.put("joinTexts", joinTexts);
        return out;
    }

    private static Map<String, Object> emptyTableJoinPath(String from, String to) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("connected", false);
        out.put("fromTable", from);
        out.put("toTable", to);
        out.put("pathLength", 0);
        out.put("path", List.of());
        out.put("joins", List.of());
        out.put("joinTexts", List.of());
        return out;
    }

    /** 解析 {@code a.id ↔ b.emp_id} 为沿 left→right 的列名对。 */
    private static String[] parseJoinDescription(String desc, String leftTable, String rightTable) {
        if (!StringUtils.hasText(desc) || !desc.contains("↔")) {
            return null;
        }
        String[] parts = desc.split("↔", 2);
        if (parts.length != 2) {
            return null;
        }
        String p0 = parts[0].trim();
        String p1 = parts[1].trim();
        int d0 = p0.indexOf('.');
        int d1 = p1.indexOf('.');
        if (d0 <= 0 || d1 <= 0) {
            return null;
        }
        String t0 = p0.substring(0, d0).trim();
        String c0 = p0.substring(d0 + 1).trim();
        String t1 = p1.substring(0, d1).trim();
        String c1 = p1.substring(d1 + 1).trim();
        if (t0.equals(leftTable) && t1.equals(rightTable)) {
            return new String[]{c0, c1};
        }
        if (t1.equals(leftTable) && t0.equals(rightTable)) {
            return new String[]{c1, c0};
        }
        return null;
    }

    private Map<String, Object> queryBetween(long graphId, String fromName, String toName,
                                             List<String> relTypes, int maxDepth) {
        if (!StringUtils.hasText(fromName) || !StringUtils.hasText(toName)) {
            throw new BizException(GraphQueryContract.BETWEEN_ERROR);
        }
        if (fromName.trim().equals(toName.trim())) {
            throw new BizException("两端不能是同一节点");
        }
        int depth = Math.max(1, Math.min(maxDepth, 6));
        boolean filterTypes = relTypes != null && !relTypes.isEmpty();
        String from = fromName.trim();
        String to = toName.trim();
        String shortestCypher = """
                MATCH (a:KgNode {graphId:$graphId, name:$fromName})
                MATCH (b:KgNode {graphId:$graphId, name:$toName})
                MATCH p = shortestPath((a)-[:KgRel*1..%d]-(b))
                WHERE all(r IN relationships(p) WHERE r.graphId = $graphId)
                RETURN p
                """.formatted(depth);
        String typedCypher = """
                MATCH (a:KgNode {graphId:$graphId, name:$fromName})
                MATCH (b:KgNode {graphId:$graphId, name:$toName})
                MATCH p = (a)-[:KgRel*1..%d]-(b)
                WHERE all(r IN relationships(p) WHERE r.graphId = $graphId AND r.relType IN $relTypes)
                RETURN p
                ORDER BY length(p) ASC
                LIMIT 1
                """.formatted(depth);
        try (Session session = driver.session()) {
            var params = Values.parameters(
                    "graphId", graphId,
                    "fromName", from,
                    "toName", to,
                    "relTypes", filterTypes ? relTypes : List.of());
            Result result = session.run(shortestCypher, params);
            if (result.hasNext()) {
                var path = result.next().get("p").asPath();
                if (!filterTypes || pathMatchesRelTypes(path, relTypes)) {
                    return packBetweenPath(path, from, to);
                }
            }
            Result typed = session.run(typedCypher, params);
            if (typed.hasNext()) {
                return packBetweenPath(typed.next().get("p").asPath(), from, to);
            }
            return emptyBetween(from, to);
        }
    }

    private static boolean pathMatchesRelTypes(org.neo4j.driver.types.Path path, List<String> relTypes) {
        for (Relationship r : path.relationships()) {
            String t = r.get("relType").asString("");
            if (!relTypes.contains(t)) {
                return false;
            }
        }
        return true;
    }

    private Map<String, Object> emptyBetween(String fromName, String toName) {
        Map<String, Object> empty = pack(new LinkedHashMap<>(), new LinkedHashMap<>(), false);
        @SuppressWarnings("unchecked")
        Map<String, Object> meta = (Map<String, Object>) empty.get("meta");
        meta.put("connected", false);
        meta.put("fromName", fromName);
        meta.put("toName", toName);
        meta.put("pathLength", 0);
        empty.put("path", List.of());
        empty.put("hops", List.of());
        return empty;
    }

    private Map<String, Object> packBetweenPath(org.neo4j.driver.types.Path path, String fromName, String toName) {
        Map<String, NodeVo> nodes = new LinkedHashMap<>();
        Map<String, EdgeVo> edges = new LinkedHashMap<>();
        List<Map<String, Object>> pathNodes = new ArrayList<>();
        List<Map<String, Object>> hops = new ArrayList<>();
        Map<String, String> elToNodeId = new HashMap<>();
        List<NodeVo> ordered = new ArrayList<>();
        for (Node n : path.nodes()) {
            NodeVo vo = toNodeVo(n);
            nodes.put(vo.getNodeId(), vo);
            elToNodeId.put(n.elementId(), vo.getNodeId());
            ordered.add(vo);
            Map<String, Object> step = new LinkedHashMap<>();
            step.put("nodeId", vo.getNodeId());
            step.put("name", vo.getName());
            step.put("gender", vo.getGender());
            step.put("nodeType", vo.getNodeType());
            pathNodes.add(step);
        }
        List<Relationship> rels = new ArrayList<>();
        path.relationships().forEach(rels::add);
        for (int i = 0; i < rels.size(); i++) {
            Relationship r = rels.get(i);
            String startId = elToNodeId.get(r.startNodeElementId());
            String endId = elToNodeId.get(r.endNodeElementId());
            EdgeVo e = toEdgeVo(r, startId, endId);
            edges.put(e.getEdgeId(), e);
            String alongFrom = ordered.get(i).getNodeId();
            String alongTo = ordered.get(i + 1).getNodeId();
            Map<String, Object> hop = new LinkedHashMap<>();
            hop.put("edgeId", e.getEdgeId());
            hop.put("relType", e.getRelType());
            hop.put("fromNodeId", startId);
            hop.put("toNodeId", endId);
            hop.put("alongFromNodeId", alongFrom);
            hop.put("alongToNodeId", alongTo);
            hop.put("forward", startId.equals(alongFrom));
            hops.add(hop);
        }
        Map<String, Object> out = pack(nodes, edges, false);
        @SuppressWarnings("unchecked")
        Map<String, Object> meta = (Map<String, Object>) out.get("meta");
        meta.put("connected", true);
        meta.put("fromName", fromName);
        meta.put("toName", toName);
        meta.put("pathLength", hops.size());
        out.put("path", pathNodes);
        out.put("hops", hops);
        return out;
    }

    private void collectDirectedPath(org.neo4j.driver.types.Path path,
                                     Map<String, NodeVo> nodes, Map<String, EdgeVo> edges) {
        Map<String, String> elToNodeId = new HashMap<>();
        for (Node n : path.nodes()) {
            NodeVo vo = toNodeVo(n);
            nodes.put(vo.getNodeId(), vo);
            elToNodeId.put(n.elementId(), vo.getNodeId());
        }
        for (Relationship r : path.relationships()) {
            EdgeVo e = toEdgeVo(r,
                    elToNodeId.get(r.startNodeElementId()),
                    elToNodeId.get(r.endNodeElementId()));
            edges.put(e.getEdgeId(), e);
        }
    }

    private Map<String, Object> queryByRelType(long graphId, List<String> relTypes, int limit) {
        if (relTypes == null || relTypes.isEmpty()) {
            throw new BizException("BY_REL_TYPE 需要 relTypes");
        }
        try (Session session = driver.session()) {
            Result result = session.run("""
                    MATCH (a:KgNode {graphId:$graphId})-[r:KgRel {graphId:$graphId}]->(b:KgNode {graphId:$graphId})
                    WHERE r.relType IN $relTypes
                    RETURN a, r, b
                    LIMIT $limit
                    """, Values.parameters("graphId", graphId, "relTypes", relTypes, "limit", limit));
            Map<String, NodeVo> nodes = new LinkedHashMap<>();
            Map<String, EdgeVo> edges = new LinkedHashMap<>();
            while (result.hasNext()) {
                Record rec = result.next();
                NodeVo a = toNodeVo(rec.get("a").asNode());
                NodeVo b = toNodeVo(rec.get("b").asNode());
                nodes.put(a.getNodeId(), a);
                nodes.put(b.getNodeId(), b);
                EdgeVo e = toEdgeVo(rec.get("r").asRelationship(), a.getNodeId(), b.getNodeId());
                edges.put(e.getEdgeId(), e);
            }
            return pack(nodes, edges, edges.size() >= limit);
        }
    }

    private Map<String, Object> querySubgraph(long graphId, String nodeName, String nodeId, int maxDepth, int limit) {
        return queryNeighbors(graphId, nodeName, nodeId, null, "BOTH", maxDepth, limit);
    }

    private Map<String, Object> collectPathLike(Result result, int limit) {
        Map<String, NodeVo> nodes = new LinkedHashMap<>();
        Map<String, EdgeVo> edges = new LinkedHashMap<>();
        int rows = 0;
        while (result.hasNext()) {
            Record rec = result.next();
            rows++;
            NodeVo n = toNodeVo(rec.get("n").asNode());
            NodeVo m = toNodeVo(rec.get("m").asNode());
            nodes.put(n.getNodeId(), n);
            nodes.put(m.getNodeId(), m);
            var relList = rec.get("r").asList(v -> v.asRelationship());
            for (Relationship r : relList) {
                EdgeVo e = toEdgeVo(r, n.getNodeId(), m.getNodeId());
                edges.put(e.getEdgeId(), e);
            }
        }
        // Fix multi-hop edges: reload edges by edgeIds
        if (!edges.isEmpty()) {
            // Re-fetch correct endpoints for each edgeId
            List<String> edgeIds = new ArrayList<>(edges.keySet());
            try (Session session = driver.session()) {
                Result fix = session.run("""
                        MATCH (a:KgNode)-[r:KgRel]->(b:KgNode)
                        WHERE r.edgeId IN $edgeIds
                        RETURN r, a.nodeId AS fromId, b.nodeId AS toId, a, b
                        """, Values.parameters("edgeIds", edgeIds));
                edges.clear();
                while (fix.hasNext()) {
                    Record rec = fix.next();
                    NodeVo a = toNodeVo(rec.get("a").asNode());
                    NodeVo b = toNodeVo(rec.get("b").asNode());
                    nodes.put(a.getNodeId(), a);
                    nodes.put(b.getNodeId(), b);
                    EdgeVo e = toEdgeVo(rec.get("r").asRelationship(),
                            rec.get("fromId").asString(), rec.get("toId").asString());
                    edges.put(e.getEdgeId(), e);
                }
            }
        }
        return pack(nodes, edges, rows >= limit);
    }

    private Map<String, Object> pack(Map<String, NodeVo> nodes, Map<String, EdgeVo> edges, boolean truncated) {
        Map<String, Object> meta = new HashMap<>();
        meta.put("truncated", truncated);
        meta.put("nodeCount", nodes.size());
        meta.put("edgeCount", edges.size());
        Map<String, Object> out = new HashMap<>();
        out.put("nodes", new ArrayList<>(nodes.values()));
        out.put("edges", new ArrayList<>(edges.values()));
        out.put("meta", meta);
        return out;
    }

    private NodeVo toNodeVo(Node n) {
        NodeVo vo = new NodeVo();
        vo.setNodeId(n.get("nodeId").asString(null));
        vo.setName(n.get("name").asString(""));
        vo.setNodeType(n.get("nodeType").asString(""));
        vo.setDescription(n.get("description").asString(""));
        Map<String, Object> props = new HashMap<>(parseProps(n.get("propsJson").asString("{}")));
        String gender = null;
        if (n.containsKey("gender") && !n.get("gender").isNull()) {
            gender = blankToNull(n.get("gender").asString(null));
        }
        if (gender == null) {
            gender = extractGenderString(props);
        }
        vo.setGender(gender);
        if (gender != null) {
            props.put("gender", gender);
        } else {
            props.remove("gender");
        }
        vo.setProps(props);
        if (n.containsKey("refKind") && !n.get("refKind").isNull()) {
            vo.setRefKind(n.get("refKind").asString());
        }
        if (n.containsKey("refId") && !n.get("refId").isNull()) {
            vo.setRefId(n.get("refId").asLong());
        }
        vo.setX(n.get("x").asDouble(0));
        vo.setY(n.get("y").asDouble(0));
        return vo;
    }

    private static String resolveGender(String gender, Map<String, Object> props) {
        if (StringUtils.hasText(gender)) {
            return gender.trim();
        }
        return extractGenderString(props);
    }

    private static String extractGenderString(Map<String, Object> props) {
        if (props == null || !props.containsKey("gender") || props.get("gender") == null) {
            return null;
        }
        String g = String.valueOf(props.get("gender")).trim();
        return g.isEmpty() || "null".equalsIgnoreCase(g) ? null : g;
    }

    private static Map<String, Object> stripGenderFromProps(Map<String, Object> props) {
        if (props == null || props.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> copy = new HashMap<>(props);
        copy.remove("gender");
        return copy;
    }

    private EdgeVo toEdgeVo(Relationship r, String fromId, String toId) {
        EdgeVo vo = new EdgeVo();
        vo.setEdgeId(r.get("edgeId").asString(null));
        vo.setFromNodeId(fromId);
        vo.setToNodeId(toId);
        vo.setRelType(r.get("relType").asString(""));
        vo.setDescription(r.get("description").asString(""));
        return vo;
    }

    private String toPropsJson(Map<String, Object> props) {
        try {
            return mapper.writeValueAsString(props == null ? Map.of() : props);
        } catch (Exception e) {
            throw new BizException("props JSON 序列化失败");
        }
    }

    private Map<String, Object> parseProps(String json) {
        try {
            return mapper.readValue(json == null ? "{}" : json, new TypeReference<>() {});
        } catch (Exception e) {
            return Map.of();
        }
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }

    private static String blankToNull(String s) {
        return StringUtils.hasText(s) ? s : null;
    }
}
