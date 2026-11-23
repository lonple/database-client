package com.lyj.dbc.graph.canvas;

import com.lyj.dbc.graph.canvas.dto.CanvasVo;
import com.lyj.dbc.graph.canvas.dto.CreateEdgeRequest;
import com.lyj.dbc.graph.canvas.dto.CreateNodeRequest;
import com.lyj.dbc.graph.canvas.dto.EdgeVo;
import com.lyj.dbc.graph.canvas.dto.NodeVo;
import com.lyj.dbc.graph.canvas.dto.UpdateEdgeRequest;
import com.lyj.dbc.graph.canvas.dto.UpdateNodeRequest;
import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.graphmeta.GraphService;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.neo4j.Neo4jGateway;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class CanvasService {
    private final GraphService graphService;
    private final Neo4jGateway neo4jGateway;

    public CanvasService(GraphService graphService, Neo4jGateway neo4jGateway) {
        this.graphService = graphService;
        this.neo4jGateway = neo4jGateway;
    }

    public CanvasVo getCanvas(Long graphId) {
        GraphEntity g = graphService.require(graphId);
        CanvasVo vo = new CanvasVo();
        vo.setGraphId(g.getId());
        vo.setName(g.getName());
        vo.setSummary(g.getSummary());
        vo.setNodes(neo4jGateway.listNodes(graphId));
        vo.setEdges(neo4jGateway.listEdges(graphId));
        return vo;
    }

    public NodeVo createNode(Long graphId, CreateNodeRequest req) {
        graphService.require(graphId);
        String name = StringUtils.hasText(req.getName()) ? req.getName().trim() : "新节点";
        return neo4jGateway.createNode(graphId, name, req.getNodeType(), req.getDescription(),
                req.getGender(), req.getProps(), req.getRefKind(), req.getRefId(), req.getX(), req.getY());
    }

    public NodeVo updateNode(Long graphId, String nodeId, UpdateNodeRequest req) {
        graphService.require(graphId);
        return neo4jGateway.updateNode(graphId, nodeId, req.getName(), req.getNodeType(),
                req.getDescription(), req.getGender(), req.getProps(), req.getRefKind(), req.getRefId());
    }

    public void updatePosition(Long graphId, String nodeId, double x, double y) {
        graphService.require(graphId);
        neo4jGateway.updatePosition(graphId, nodeId, x, y);
    }

    public void deleteNode(Long graphId, String nodeId) {
        graphService.require(graphId);
        neo4jGateway.deleteNode(graphId, nodeId);
    }

    public EdgeVo createEdge(Long graphId, CreateEdgeRequest req) {
        graphService.require(graphId);
        if (!StringUtils.hasText(req.getFromNodeId()) || !StringUtils.hasText(req.getToNodeId())) {
            throw new BizException("起止节点不能为空");
        }
        return neo4jGateway.createEdge(graphId, req.getFromNodeId(), req.getToNodeId(),
                req.getRelType(), req.getDescription());
    }

    public EdgeVo updateEdge(Long graphId, String edgeId, UpdateEdgeRequest req) {
        graphService.require(graphId);
        return neo4jGateway.updateEdge(graphId, edgeId, req.getRelType(), req.getDescription());
    }

    public void deleteEdge(Long graphId, String edgeId) {
        graphService.require(graphId);
        neo4jGateway.deleteEdge(graphId, edgeId);
    }
}
