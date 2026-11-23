package com.lyj.dbc.knowledge.knowledge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.knowledge.llm.client.LlmClient;
import com.lyj.dbc.knowledge.llm.model.ChatMessage;
import com.lyj.dbc.knowledge.llm.model.ChatRequest;
import com.lyj.dbc.knowledge.llm.model.ChatResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import org.springframework.util.StreamUtils;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CategoryRecommendService {
    private static final Logger log = LoggerFactory.getLogger(CategoryRecommendService.class);

    private final LlmClient llmClient;
    private final CategoryService categoryService;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String promptTemplate;

    public CategoryRecommendService(LlmClient llmClient, CategoryService categoryService) {
        this.llmClient = llmClient;
        this.categoryService = categoryService;
        this.promptTemplate = loadPrompt();
    }

    public Map<String, Object> recommend(String title, String summary, String body) {
        Map<String, Object> result = new HashMap<>();
        result.put("categoryId", null);
        result.put("pathLabel", null);
        result.put("reason", "no recommendation");
        try {
            String treeJson = objectMapper.writeValueAsString(categoryService.tree());
            String user = promptTemplate
                    .replace("{{title}}", nullToEmpty(title))
                    .replace("{{summary}}", nullToEmpty(summary))
                    .replace("{{body}}", truncate(nullToEmpty(body), 4000))
                    .replace("{{categoryTree}}", treeJson);
            ChatResponse resp = llmClient.chat(ChatRequest.builder()
                    .caller("memory")
                    .responseFormat("json_object")
                    .temperature(0.1)
                    .messages(List.of(
                            ChatMessage.system("Recommend a category. JSON only."),
                            ChatMessage.user(user)
                    ))
                    .build());
            JsonNode root = objectMapper.readTree(resp.getContent());
            if (root.has("categoryId") && !root.get("categoryId").isNull()) {
                long id = root.get("categoryId").asLong();
                result.put("categoryId", id);
                result.put("pathLabel", categoryService.pathLabel(id));
            }
            if (root.has("reason")) {
                result.put("reason", root.path("reason").asText());
            }
        } catch (Exception e) {
            log.warn("category recommend failed: {}", e.getMessage());
            result.put("reason", "LLM unavailable: " + e.getMessage());
        }
        return result;
    }

    private String loadPrompt() {
        try {
            return StreamUtils.copyToString(
                    new ClassPathResource("prompts/category_recommend.md").getInputStream(),
                    StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "Title: {{title}}\nSummary: {{summary}}\nBody:\n{{body}}\nTree: {{categoryTree}}\nJSON: {\"categoryId\":null,\"reason\":\"\"}";
        }
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max);
    }
}
