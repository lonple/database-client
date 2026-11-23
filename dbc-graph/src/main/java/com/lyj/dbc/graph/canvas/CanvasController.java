package com.lyj.dbc.graph.canvas;

import com.lyj.dbc.graph.canvas.dto.CanvasVo;
import com.lyj.dbc.graph.canvas.dto.CreateEdgeRequest;
import com.lyj.dbc.graph.canvas.dto.CreateNodeRequest;
import com.lyj.dbc.graph.canvas.dto.EdgeVo;
import com.lyj.dbc.graph.canvas.dto.NodeVo;
import com.lyj.dbc.graph.canvas.dto.UpdateEdgeRequest;
import com.lyj.dbc.graph.canvas.dto.UpdateNodeRequest;
import com.lyj.dbc.graph.canvas.dto.UpdatePositionRequest;
import com.lyj.dbc.graph.common.api.ApiResponse;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/graphs/{graphId}")
public class CanvasController {
    private final CanvasService canvasService;

    public CanvasController(CanvasService canvasService) {
        this.canvasService = canvasService;
    }

    @GetMapping("/canvas")
    public ApiResponse<CanvasVo> canvas(@PathVariable Long graphId) {
        return ApiResponse.ok(canvasService.getCanvas(graphId));
    }

    @PostMapping("/nodes")
    public ApiResponse<NodeVo> createNode(@PathVariable Long graphId, @RequestBody CreateNodeRequest req) {
        return ApiResponse.ok(canvasService.createNode(graphId, req));
    }

    @PatchMapping("/nodes/{nodeId}")
    public ApiResponse<NodeVo> updateNode(@PathVariable Long graphId, @PathVariable String nodeId,
                                          @RequestBody UpdateNodeRequest req) {
        return ApiResponse.ok(canvasService.updateNode(graphId, nodeId, req));
    }

    @PatchMapping("/nodes/{nodeId}/position")
    public ApiResponse<Void> updatePosition(@PathVariable Long graphId, @PathVariable String nodeId,
                                            @RequestBody UpdatePositionRequest req) {
        canvasService.updatePosition(graphId, nodeId, req.getX(), req.getY());
        return ApiResponse.ok(null);
    }

    @DeleteMapping("/nodes/{nodeId}")
    public ApiResponse<Void> deleteNode(@PathVariable Long graphId, @PathVariable String nodeId) {
        canvasService.deleteNode(graphId, nodeId);
        return ApiResponse.ok(null);
    }

    @PostMapping("/edges")
    public ApiResponse<EdgeVo> createEdge(@PathVariable Long graphId, @RequestBody CreateEdgeRequest req) {
        return ApiResponse.ok(canvasService.createEdge(graphId, req));
    }

    @PatchMapping("/edges/{edgeId}")
    public ApiResponse<EdgeVo> updateEdge(@PathVariable Long graphId, @PathVariable String edgeId,
                                          @RequestBody UpdateEdgeRequest req) {
        return ApiResponse.ok(canvasService.updateEdge(graphId, edgeId, req));
    }

    @DeleteMapping("/edges/{edgeId}")
    public ApiResponse<Void> deleteEdge(@PathVariable Long graphId, @PathVariable String edgeId) {
        canvasService.deleteEdge(graphId, edgeId);
        return ApiResponse.ok(null);
    }
}
