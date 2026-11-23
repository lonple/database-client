package com.lyj.dbc.graph.query;

import com.lyj.dbc.graph.common.api.ApiResponse;
import com.lyj.dbc.graph.query.dto.BetweenRelationRequest;
import com.lyj.dbc.graph.query.dto.GraphQueryRequest;
import com.lyj.dbc.graph.query.dto.TableJoinPathRequest;
import com.lyj.dbc.graph.query.dto.TableNeighborsRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/graphs/{graphId}")
public class QueryController {
    private final QueryService queryService;

    public QueryController(QueryService queryService) {
        this.queryService = queryService;
    }

    @GetMapping("/query/guide")
    public ApiResponse<String> queryGuide(@PathVariable Long graphId) {
        queryService.requireGraph(graphId);
        return ApiResponse.ok(GraphQueryContract.GUIDE);
    }

    /**
     * 通用关系查询。mode 含 BETWEEN（两人无向最短路）。
     * 称谓解读：父母边方向 + nodes[].gender（一级属性）。契约见 GET /query/guide。
     */
    @PostMapping("/query")
    public ApiResponse<Map<String, Object>> query(@PathVariable Long graphId,
                                                  @RequestBody GraphQueryRequest req) {
        return ApiResponse.ok(queryService.query(graphId, req));
    }

    /**
     * 查询两个人物节点之间的关系路径（无向有界最短路）。
     * 等价于 POST /query 且 mode=BETWEEN；返回 path、hops、nodes（含 gender）。
     */
    @PostMapping("/relations/between")
    public ApiResponse<Map<String, Object>> between(@PathVariable Long graphId,
                                                    @RequestBody BetweenRelationRequest req) {
        return ApiResponse.ok(queryService.between(graphId, req));
    }

    /**
     * 两表最短关联路径。返回 joins[].text，形如 {@code t0.id 关联 t1.t0_id}。
     * 依赖图谱中父子列双向边（父列 / 子列作 relType）。
     */
    @PostMapping("/table-join-path")
    public ApiResponse<Map<String, Object>> tableJoinPath(@PathVariable Long graphId,
                                                          @RequestBody TableJoinPathRequest req) {
        return ApiResponse.ok(queryService.tableJoinPath(graphId, req));
    }

    /**
     * 某表的无向邻接表。返回 neighbors[].joinTexts，形如 {@code t0.id 关联 t1.t0_id}。
     */
    @PostMapping("/table-neighbors")
    public ApiResponse<Map<String, Object>> tableNeighbors(@PathVariable Long graphId,
                                                           @RequestBody TableNeighborsRequest req) {
        return ApiResponse.ok(queryService.tableNeighbors(graphId, req));
    }
}
