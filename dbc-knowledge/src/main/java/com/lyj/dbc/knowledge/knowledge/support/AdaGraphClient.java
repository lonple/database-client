package com.lyj.dbc.knowledge.knowledge.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 旁路调用 ada-graph：表邻接查询。
 */
@Component
@EnableConfigurationProperties(AdaGraphProperties.class)
public class AdaGraphClient {
    private static final Logger log = LoggerFactory.getLogger(AdaGraphClient.class);

    private final AdaGraphProperties properties;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public AdaGraphClient(AdaGraphProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(Math.max(1000, properties.getTimeoutMs())))
                .build();
    }

    /**
     * POST /api/graphs/{graphId}/table-neighbors
     * 失败时返回空 neighbors，不阻断找表主流程。
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> tableNeighbors(long graphId, String table, int maxDepth, int limit) {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("table", table);
        empty.put("neighbors", List.of());
        if (!StringUtils.hasText(table) || !StringUtils.hasText(properties.getBaseUrl())) {
            return empty;
        }
        try {
            String base = properties.getBaseUrl().replaceAll("/+$", "");
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("table", table.trim());
            body.put("maxDepth", maxDepth);
            body.put("limit", limit);
            String json = objectMapper.writeValueAsString(body);
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(base + "/api/graphs/" + graphId + "/table-neighbors"))
                    .timeout(Duration.ofMillis(Math.max(1000, properties.getTimeoutMs())))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();
            HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() >= 400) {
                log.warn("ada-graph table-neighbors HTTP {} body={}", resp.statusCode(),
                        truncate(resp.body()));
                return empty;
            }
            JsonNode root = objectMapper.readTree(resp.body());
            JsonNode data = root.has("data") ? root.get("data") : root;
            if (data == null || data.isNull()) {
                return empty;
            }
            return objectMapper.convertValue(data, Map.class);
        } catch (Exception e) {
            log.warn("ada-graph table-neighbors 调用失败 graphId={} table={}", graphId, table, e);
            return empty;
        }
    }

    private static String truncate(String s) {
        if (s == null) {
            return "";
        }
        return s.length() <= 300 ? s : s.substring(0, 300);
    }
}
