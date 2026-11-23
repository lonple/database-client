package com.lyj.dbc.knowledge.llm.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.error.LlmException;
import com.lyj.dbc.knowledge.llm.model.RerankHit;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * DashScope 原生 text-rerank（非 OpenAI 兼容路径）。
 */
final class DashScopeRerankClient {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    private final LlmProperties properties;

    DashScopeRerankClient(LlmProperties properties) {
        this.properties = properties;
    }

    List<RerankHit> rerank(String query, List<String> documents) {
        if (documents == null || documents.isEmpty()) {
            return List.of();
        }
        String key = firstKey();
        if (!StringUtils.hasText(key)) {
            throw new LlmException("LLM rerank disabled: set dbc.knowledge.llm.api-key or dbc.knowledge.llm.rerank-api-key");
        }
        String url = StringUtils.hasText(properties.getRerankUrl())
                ? properties.getRerankUrl().trim()
                : "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank";
        String model = StringUtils.hasText(properties.getRerankModel())
                ? properties.getRerankModel().trim()
                : "qwen3-rerank";
        String body = buildBody(query, documents, model, url);
        int attempts = Math.max(1, properties.getMaxRetries() + 1);
        Duration timeout = Duration.ofMillis(Math.max(1_000, properties.getTimeoutMs()));
        Exception last = null;
        for (int i = 0; i < attempts; i++) {
            try {
                HttpRequest req = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .timeout(timeout)
                        .header("Authorization", "Bearer " + key)
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                        .build();
                HttpResponse<String> resp = HTTP.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
                int code = resp.statusCode();
                if (code >= 200 && code < 300) {
                    return parse(resp.body(), documents.size());
                }
                if (code == 429 || code >= 500) {
                    last = new LlmException("LLM rerank HTTP " + code + ": " + abbreviate(resp.body()));
                    continue;
                }
                throw new LlmException("LLM rerank HTTP " + code + ": " + abbreviate(resp.body()));
            } catch (LlmException e) {
                throw e;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new LlmException("LLM rerank interrupted", e);
            } catch (Exception e) {
                last = e;
            }
        }
        throw new LlmException("LLM rerank failed: " + (last == null ? "unknown" : last.getMessage()), last);
    }

    private String firstKey() {
        if (StringUtils.hasText(properties.getRerankApiKey())) {
            return properties.getRerankApiKey().trim();
        }
        if (StringUtils.hasText(properties.getApiKey())) {
            return properties.getApiKey().trim();
        }
        return "";
    }

    private static String buildBody(String query, List<String> documents, String model, String url) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("model", model);
        if (isCompatibleReranks(url)) {
            root.put("query", query == null ? "" : query);
            ArrayNode docs = root.putArray("documents");
            for (String d : documents) {
                docs.add(d == null ? "" : d);
            }
            root.put("top_n", documents.size());
        } else {
            ObjectNode input = root.putObject("input");
            input.put("query", query == null ? "" : query);
            ArrayNode docs = input.putArray("documents");
            for (String d : documents) {
                docs.add(d == null ? "" : d);
            }
            ObjectNode params = root.putObject("parameters");
            params.put("top_n", documents.size());
            params.put("return_documents", false);
        }
        try {
            return MAPPER.writeValueAsString(root);
        } catch (Exception e) {
            throw new LlmException("LLM rerank serialize failed: " + e.getMessage(), e);
        }
    }

    static boolean isCompatibleReranks(String url) {
        return url != null && url.contains("/reranks");
    }

    static List<RerankHit> parse(String raw, int docCount) {
        try {
            JsonNode root = MAPPER.readTree(raw == null ? "{}" : raw);
            JsonNode results = root.path("output").path("results");
            if (!results.isArray() || results.isEmpty()) {
                results = root.path("results");
            }
            if (!results.isArray() || results.isEmpty()) {
                throw new LlmException("LLM rerank empty results: " + abbreviate(raw));
            }
            List<RerankHit> hits = new ArrayList<>();
            boolean[] seen = new boolean[Math.max(docCount, 0)];
            for (JsonNode n : results) {
                int index = n.path("index").asInt(-1);
                if (index < 0 || index >= docCount || (index < seen.length && seen[index])) {
                    continue;
                }
                double score = n.has("relevance_score")
                        ? n.path("relevance_score").asDouble(0)
                        : n.path("score").asDouble(0);
                hits.add(new RerankHit(index, score));
                if (index < seen.length) {
                    seen[index] = true;
                }
            }
            if (hits.isEmpty()) {
                throw new LlmException("LLM rerank no valid indices: " + abbreviate(raw));
            }
            return hits;
        } catch (LlmException e) {
            throw e;
        } catch (Exception e) {
            throw new LlmException("LLM rerank parse failed: " + e.getMessage(), e);
        }
    }

    private static String abbreviate(String s) {
        if (s == null) {
            return "";
        }
        String t = s.replace('\n', ' ').trim();
        return t.length() <= 240 ? t : t.substring(0, 240) + "...";
    }
}
