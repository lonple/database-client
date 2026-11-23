package com.lyj.dbc.graph.query;

import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.graphmeta.GraphService;
import com.lyj.dbc.graph.neo4j.Neo4jGateway;
import com.lyj.dbc.graph.query.dto.BetweenRelationRequest;
import com.lyj.dbc.graph.query.dto.GraphQueryRequest;
import com.lyj.dbc.graph.query.dto.TableJoinPathRequest;
import com.lyj.dbc.graph.query.dto.TableNeighborsRequest;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.Map;

@Service
public class QueryService {
    private final GraphService graphService;
    private final Neo4jGateway neo4jGateway;

    public QueryService(GraphService graphService, Neo4jGateway neo4jGateway) {
        this.graphService = graphService;
        this.neo4jGateway = neo4jGateway;
    }

    public void requireGraph(Long graphId) {
        graphService.require(graphId);
    }

    public Map<String, Object> query(Long graphId, GraphQueryRequest req) {
        graphService.require(graphId);
        validate(req);
        String mode = req.getMode() == null ? "NEIGHBORS" : req.getMode().trim().toUpperCase();
        int defaultDepth = "BETWEEN".equals(mode) ? 6 : 2;
        int maxDepth = clamp(req.getMaxDepth(), defaultDepth, 1, 6);
        int limit = clamp(req.getLimit(), 50, 1, 200);
        Map<String, Object> result = neo4jGateway.query(
                graphId,
                mode,
                req.getNodeName(),
                req.getNodeId(),
                req.getToNodeName(),
                req.getRelTypes(),
                req.getDirection(),
                maxDepth,
                limit);
        @SuppressWarnings("unchecked")
        Map<String, Object> meta = (Map<String, Object>) result.get("meta");
        if (meta != null) {
            meta.put("mode", mode);
        }
        return result;
    }

    /** 两人关系：无向有界最短路径。 */
    public Map<String, Object> between(Long graphId, BetweenRelationRequest req) {
        if (req == null) {
            throw new BizException(GraphQueryContract.BETWEEN_ERROR);
        }
        GraphQueryRequest q = new GraphQueryRequest();
        q.setMode("BETWEEN");
        q.setNodeName(req.getFromName());
        q.setToNodeName(req.getToName());
        q.setRelTypes(req.getRelTypes());
        q.setMaxDepth(req.getMaxDepth());
        return query(graphId, q);
    }

    /** 两表 JOIN 路径：无向最短路 + 双向边解析为「a.col 关联 b.col」。 */
    public Map<String, Object> tableJoinPath(Long graphId, TableJoinPathRequest req) {
        graphService.require(graphId);
        if (req == null || !StringUtils.hasText(req.getFromTable()) || !StringUtils.hasText(req.getToTable())) {
            throw new BizException("table-join-path 需要 fromTable 与 toTable");
        }
        int maxDepth = clamp(req.getMaxDepth(), 6, 1, 8);
        return neo4jGateway.queryTableJoinPath(graphId, req.getFromTable(), req.getToTable(), maxDepth);
    }

    /** 某表的无向邻接表 + JOIN 列。 */
    public Map<String, Object> tableNeighbors(Long graphId, TableNeighborsRequest req) {
        graphService.require(graphId);
        if (req == null || !StringUtils.hasText(req.getTable())) {
            throw new BizException("table-neighbors 需要 table");
        }
        int maxDepth = clamp(req.getMaxDepth(), 1, 1, 3);
        int limit = clamp(req.getLimit(), 50, 1, 200);
        return neo4jGateway.queryTableNeighbors(graphId, req.getTable(), maxDepth, limit);
    }

    private static void validate(GraphQueryRequest req) {
        if (req == null) {
            throw new BizException(GraphQueryContract.NEIGHBORS_ERROR);
        }
        String mode = req.getMode() == null ? "NEIGHBORS" : req.getMode().trim().toUpperCase();
        boolean hasStart = StringUtils.hasText(req.getNodeName()) || StringUtils.hasText(req.getNodeId());
        switch (mode) {
            case "PATH", "BETWEEN" -> {
                if (!StringUtils.hasText(req.getNodeName()) || !StringUtils.hasText(req.getToNodeName())) {
                    throw new BizException("BETWEEN".equals(mode)
                            ? GraphQueryContract.BETWEEN_ERROR
                            : GraphQueryContract.PATH_ERROR);
                }
            }
            case "BY_REL_TYPE" -> {
                if (req.getRelTypes() == null || req.getRelTypes().isEmpty()) {
                    throw new BizException(GraphQueryContract.REL_TYPE_ERROR);
                }
            }
            case "NEIGHBORS", "SUBGRAPH" -> {
                if (!hasStart) {
                    throw new BizException(GraphQueryContract.NEIGHBORS_ERROR);
                }
            }
            default -> {
            }
        }
    }

    private static int clamp(Integer v, int def, int min, int max) {
        if (v == null) {
            return def;
        }
        return Math.max(min, Math.min(max, v));
    }
}
