package com.lyj.dbc.graph.seed;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.graph.category.CategoryService;
import com.lyj.dbc.graph.category.dto.CategoryCreateRequest;
import com.lyj.dbc.graph.category.entity.GraphCategoryEntity;
import com.lyj.dbc.graph.category.mapper.GraphCategoryMapper;
import com.lyj.dbc.graph.graphmeta.GraphService;
import com.lyj.dbc.graph.graphmeta.dto.GraphCreateRequest;
import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import com.lyj.dbc.graph.neo4j.Neo4jGateway;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 从 company 库表外键元数据构建「表关系」图谱。
 * <p>
 * 规则：外键 {@code 子表.childCol → 父表.parentCol}（如 {@code b.a_id → a.id}）生成双向边：
 * <ul>
 *   <li>父表 → 子表，{@code relType = parentCol}（如 {@code id}）</li>
 *   <li>子表 → 父表，{@code relType = childCol}（如 {@code a_id}）</li>
 * </ul>
 * 节点名为表名，{@code nodeType=表}。
 */
@Component
@Order(21)
public class CompanyTableRelationsSeed implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(CompanyTableRelationsSeed.class);
    public static final String GRAPH_NAME = "company 表关系";
    private static final String RESOURCE = "seed/company-table-fks.json";

    private final boolean enabled;
    private final CategoryService categoryService;
    private final GraphCategoryMapper categoryMapper;
    private final GraphService graphService;
    private final Neo4jGateway neo4jGateway;
    private final ObjectMapper objectMapper;

    public CompanyTableRelationsSeed(
            @Value("${dbc.graph.seed.company-table-relations:false}") boolean enabled,
            CategoryService categoryService,
            GraphCategoryMapper categoryMapper,
            GraphService graphService,
            Neo4jGateway neo4jGateway,
            ObjectMapper objectMapper) {
        this.enabled = enabled;
        this.categoryService = categoryService;
        this.categoryMapper = categoryMapper;
        this.graphService = graphService;
        this.neo4jGateway = neo4jGateway;
        this.objectMapper = objectMapper;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (!enabled) {
            return;
        }
        Exception last = null;
        for (int i = 1; i <= 5; i++) {
            try {
                ensureSeeded(false);
                return;
            } catch (Exception e) {
                last = e;
                log.warn("company 表关系种子第 {}/5 次失败: {}", i, e.getMessage());
                try {
                    Thread.sleep(2000L * i);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        log.warn("company 表关系种子最终失败（可 POST /api/admin/seed/company-table-relations?force=true）: {}",
                last == null ? "" : last.getMessage());
    }

    /** @param force 为 true 时若已存在则先删再重建 */
    public GraphEntity ensureSeeded(boolean force) {
        GraphEntity existing = graphService.findByName(GRAPH_NAME);
        if (existing != null) {
            int nodeCount = neo4jGateway.listNodes(existing.getId()).size();
            if (!force && nodeCount > 0) {
                log.info("表关系图谱已存在，跳过种子: id={} nodes={}", existing.getId(), nodeCount);
                return existing;
            }
            try {
                graphService.delete(existing.getId());
            } catch (Exception e) {
                log.warn("清理旧表关系图谱失败 id={}: {}", existing.getId(), e.getMessage());
                neo4jGateway.deleteGraphData(existing.getId());
            }
        }
        return seed();
    }

    private GraphEntity seed() {
        neo4jGateway.listNodes(-1L);
        JsonNode root = loadResource();
        int tableCount = root.path("tableCount").asInt();
        int fkCount = root.path("fkCount").asInt();

        Long categoryId = ensureCategory("示例数据");
        GraphCreateRequest create = new GraphCreateRequest();
        create.setCategoryId(categoryId);
        create.setCode("default");
        create.setName(GRAPH_NAME);
        create.setProductName("dbc产品");
        create.setSummary("demo-company 库表外键图谱：节点为表名；"
                + "每条 FK（子表.col → 父表.col）生成双向边，父→子边类型为父列名，子→父边类型为子列名。"
                + "共 " + tableCount + " 表 / " + fkCount + " FK（" + (fkCount * 2) + " 有向边）。");
        GraphEntity graph = graphService.create(create);
        long gid = graph.getId();
        try {
            fillGraph(gid, root);
            log.info("已初始化「{}」graphId={} tables={} fks={}", GRAPH_NAME, gid, tableCount, fkCount);
            return graph;
        } catch (Exception e) {
            try {
                graphService.delete(gid);
            } catch (Exception ignored) {
                neo4jGateway.deleteGraphData(gid);
            }
            throw e;
        }
    }

    private void fillGraph(long gid, JsonNode root) {
        Map<String, String> nameToId = new LinkedHashMap<>();
        List<Map<String, Object>> nodeRows = new ArrayList<>();

        // 按业务域分列布局
        Map<String, List<JsonNode>> byDomain = new LinkedHashMap<>();
        for (JsonNode t : root.path("tables")) {
            String domain = t.path("domain").asText("other");
            byDomain.computeIfAbsent(domain, k -> new ArrayList<>()).add(t);
        }
        List<String> domains = new ArrayList<>(byDomain.keySet());
        double colGap = 220;
        double rowGap = 70;
        for (int di = 0; di < domains.size(); di++) {
            List<JsonNode> tables = byDomain.get(domains.get(di));
            double x = 40 + di * colGap;
            for (int ti = 0; ti < tables.size(); ti++) {
                JsonNode t = tables.get(ti);
                String name = t.path("name").asText();
                boolean core = t.path("core").asBoolean(false);
                String domain = t.path("domain").asText();
                String nodeId = UUID.randomUUID().toString();
                nameToId.put(name, nodeId);

                Map<String, Object> props = new HashMap<>();
                props.put("domain", domain);
                props.put("core", core);
                String propsJson;
                try {
                    propsJson = objectMapper.writeValueAsString(props);
                } catch (Exception e) {
                    propsJson = "{}";
                }

                Map<String, Object> row = new HashMap<>();
                row.put("nodeId", nodeId);
                row.put("name", name);
                row.put("nodeType", "表");
                row.put("description", core ? "核心表 · " + domain : "扩展表 · " + domain);
                row.put("gender", null);
                row.put("propsJson", propsJson);
                row.put("refKind", null);
                row.put("refId", null);
                row.put("x", x);
                row.put("y", 40 + ti * rowGap);
                nodeRows.add(row);
            }
        }
        int n = neo4jGateway.bulkCreateNodes(gid, nodeRows);

        List<Map<String, Object>> edgeRows = new ArrayList<>();
        for (JsonNode fk : root.path("fks")) {
            String child = fk.path("child").asText();
            String childCol = fk.path("childCol").asText();
            String parent = fk.path("parent").asText();
            String parentCol = fk.path("parentCol").asText();
            String parentId = nameToId.get(parent);
            String childId = nameToId.get(child);
            if (parentId == null || childId == null) {
                throw new IllegalStateException("FK 端点表缺失: " + child + " / " + parent);
            }
            String desc = parent + "." + parentCol + " ↔ " + child + "." + childCol;
            // 父 → 子：边类型 = 父列（如 id）
            edgeRows.add(edgeRow(parentId, childId, parentCol, desc));
            // 子 → 父：边类型 = 子列（如 a_id / emp_id）
            edgeRows.add(edgeRow(childId, parentId, childCol, desc));
        }
        int e = neo4jGateway.bulkCreateEdges(gid, edgeRows);
        log.info("表关系写入完成 nodes={} edges={}", n, e);
    }

    private static Map<String, Object> edgeRow(String fromId, String toId, String relType, String description) {
        Map<String, Object> row = new HashMap<>();
        row.put("edgeId", UUID.randomUUID().toString());
        row.put("fromId", fromId);
        row.put("toId", toId);
        row.put("relType", relType);
        row.put("description", description);
        return row;
    }

    private JsonNode loadResource() {
        try (InputStream in = new ClassPathResource(RESOURCE).getInputStream()) {
            return objectMapper.readTree(in);
        } catch (Exception e) {
            throw new IllegalStateException("无法加载 " + RESOURCE + ": " + e.getMessage(), e);
        }
    }

    private Long ensureCategory(String name) {
        GraphCategoryEntity found = categoryMapper.selectOne(new LambdaQueryWrapper<GraphCategoryEntity>()
                .eq(GraphCategoryEntity::getName, name)
                .isNull(GraphCategoryEntity::getParentId)
                .last("LIMIT 1"));
        if (found != null) {
            return found.getId();
        }
        CategoryCreateRequest req = new CategoryCreateRequest();
        req.setName(name);
        return categoryService.create(req).getId();
    }
}
