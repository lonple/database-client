package com.lyj.dbc.graph.graphmeta;

import com.lyj.dbc.graph.common.api.BizException;
import com.lyj.dbc.graph.graphmeta.dto.GraphCreateRequest;
import com.lyj.dbc.graph.graphmeta.dto.TableRelationImportRequest;
import com.lyj.dbc.graph.graphmeta.dto.TableRelationImportResult;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.neo4j.Neo4jGateway;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

@Service
public class TableRelationImportService {
    private static final Logger log = LoggerFactory.getLogger(TableRelationImportService.class);

    private final GraphService graphService;
    private final Neo4jGateway neo4jGateway;

    public TableRelationImportService(GraphService graphService, Neo4jGateway neo4jGateway) {
        this.graphService = graphService;
        this.neo4jGateway = neo4jGateway;
    }

    public TableRelationImportResult importMarkdown(TableRelationImportRequest req) {
        if (req == null || !StringUtils.hasText(req.getMarkdown())) {
            throw new BizException("markdown 不能为空");
        }
        TableRelationMdParser.Parsed parsed = TableRelationMdParser.parse(req.getMarkdown());
        String code = firstNonBlank(req.getCode(), parsed.code());
        String name = firstNonBlank(req.getName(), parsed.name());
        String summary = firstNonBlank(req.getSummary(), parsed.summary());
        String productName = firstNonBlank(req.getProductName(), parsed.productName());
        boolean force = Boolean.TRUE.equals(req.getForce());

        boolean replaced = false;
        GraphEntity existing = graphService.findByCode(code);
        if (existing != null) {
            if (!force) {
                throw new BizException("图谱编码已存在: " + code + "（可勾选强制覆盖）");
            }
            try {
                graphService.delete(existing.getId());
            } catch (Exception e) {
                log.warn("删除旧图谱失败 id={}: {}", existing.getId(), e.getMessage());
                neo4jGateway.deleteGraphData(existing.getId());
            }
            replaced = true;
        }

        GraphCreateRequest create = new GraphCreateRequest();
        create.setCode(code);
        create.setName(name);
        create.setSummary(summary);
        create.setProductName(productName);
        GraphEntity graph = graphService.create(create);
        long gid = graph.getId();
        try {
            FillStats stats = fillGraph(gid, parsed);
            TableRelationImportResult result = new TableRelationImportResult();
            result.setGraph(graph);
            result.setTableCount(parsed.tables().size());
            result.setFkCount(parsed.fks().size());
            result.setNodeCount(stats.nodeCount());
            result.setEdgeCount(stats.edgeCount());
            result.setReplaced(replaced);
            log.info("表关系 MD 导入完成 graphId={} code={} tables={} fks={} edges={}",
                    gid, code, result.getTableCount(), result.getFkCount(), result.getEdgeCount());
            return result;
        } catch (RuntimeException e) {
            try {
                graphService.delete(gid);
            } catch (Exception ignored) {
                neo4jGateway.deleteGraphData(gid);
            }
            throw e;
        }
    }

    private FillStats fillGraph(long gid, TableRelationMdParser.Parsed parsed) {
        // 按表名前缀分列布局
        Map<String, List<String>> byDomain = new LinkedHashMap<>();
        for (String table : parsed.tables()) {
            byDomain.computeIfAbsent(domainOf(table), k -> new ArrayList<>()).add(table);
        }

        Map<String, String> nameToId = new LinkedHashMap<>();
        List<Map<String, Object>> nodeRows = new ArrayList<>();
        List<String> domains = new ArrayList<>(byDomain.keySet());
        double colGap = 220;
        double rowGap = 70;
        for (int di = 0; di < domains.size(); di++) {
            List<String> tables = byDomain.get(domains.get(di));
            double x = 40 + di * colGap;
            for (int ti = 0; ti < tables.size(); ti++) {
                String table = tables.get(ti);
                String nodeId = UUID.randomUUID().toString();
                nameToId.put(table, nodeId);
                Map<String, Object> row = new HashMap<>();
                row.put("nodeId", nodeId);
                row.put("name", table);
                row.put("nodeType", "表");
                row.put("description", "域 · " + domains.get(di));
                row.put("gender", null);
                row.put("propsJson", "{\"domain\":\"" + domains.get(di) + "\"}");
                row.put("refKind", null);
                row.put("refId", null);
                row.put("x", x);
                row.put("y", 40 + ti * rowGap);
                nodeRows.add(row);
            }
        }
        int nodeCount = neo4jGateway.bulkCreateNodes(gid, nodeRows);

        List<Map<String, Object>> edgeRows = new ArrayList<>();
        for (TableRelationMdParser.FkRow fk : parsed.fks()) {
            String parentId = nameToId.get(fk.parent());
            String childId = nameToId.get(fk.child());
            if (parentId == null || childId == null) {
                throw new BizException("FK 端点表缺失: " + fk.child() + " / " + fk.parent());
            }
            String desc = StringUtils.hasText(fk.description())
                    ? fk.description()
                    : fk.parent() + "." + fk.parentCol() + " ↔ " + fk.child() + "." + fk.childCol();
            if (parsed.bidirectional()) {
                edgeRows.add(edgeRow(parentId, childId, fk.parentCol(), desc));
                edgeRows.add(edgeRow(childId, parentId, fk.childCol(), desc));
            } else {
                // 单向：子 → 父，边类型=子列
                edgeRows.add(edgeRow(childId, parentId, fk.childCol(), desc));
            }
        }
        int edgeCount = neo4jGateway.bulkCreateEdges(gid, edgeRows);
        return new FillStats(nodeCount, edgeCount);
    }

    private static Map<String, Object> edgeRow(String fromId, String toId, String relType, String description) {
        Map<String, Object> row = new HashMap<>();
        row.put("edgeId", UUID.randomUUID().toString());
        row.put("fromId", fromId);
        row.put("toId", toId);
        row.put("relType", relType);
        row.put("description", description == null ? "" : description);
        return row;
    }

    private static String domainOf(String table) {
        if (!StringUtils.hasText(table)) {
            return "other";
        }
        int us = table.indexOf('_');
        if (us > 0) {
            return table.substring(0, us).toLowerCase(Locale.ROOT);
        }
        return "other";
    }

    private static String firstNonBlank(String a, String b) {
        if (StringUtils.hasText(a)) {
            return a.trim();
        }
        return b;
    }

    private record FillStats(int nodeCount, int edgeCount) {
    }
}
