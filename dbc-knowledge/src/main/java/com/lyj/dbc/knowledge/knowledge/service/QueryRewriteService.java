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
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 将用户口语问句改写成贴近入库向量文本的检索语：主题短语 + 正文检索语。
 */
@Service
public class QueryRewriteService {
    private static final Logger log = LoggerFactory.getLogger(QueryRewriteService.class);

    private static final Pattern CHAT_PREFIX = Pattern.compile(
            "^(请|麻烦|劳驾)?(帮我|帮忙|帮)?(看一下|看下|看看|查一下|查下|查查|说一下|说下|问一下|问下)?");
    private static final Pattern TRAILING_NOISE = Pattern.compile("[？?！!。．…~～]+$");

    private final LlmClient llmClient;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final String promptTemplate;

    public QueryRewriteService(LlmClient llmClient) {
        this.llmClient = llmClient;
        this.promptTemplate = loadPrompt();
    }

    public RewrittenQuery rewrite(String productName, String rawQuery) {
        String raw = rawQuery == null ? "" : rawQuery.trim();
        if (!StringUtils.hasText(raw)) {
            return RewrittenQuery.fallback(raw);
        }
        try {
            String user = promptTemplate
                    .replace("{{productName}}", productName == null ? "" : productName.trim())
                    .replace("{{query}}", truncate(raw, 500));
            ChatResponse resp = llmClient.chat(ChatRequest.builder()
                    .caller("memory-search")
                    .responseFormat("json_object")
                    .temperature(0.1)
                    .messages(List.of(
                            ChatMessage.system(
                                    "Rewrite the user question for knowledge retrieval. JSON only. Do not answer."),
                            ChatMessage.user(user)
                    ))
                    .build());
            RewrittenQuery parsed = parse(raw, resp.getContent());
            if (parsed != null) {
                return parsed;
            }
        } catch (Exception e) {
            log.warn("query rewrite failed, use rule fallback: {}", e.getMessage());
        }
        return ruleFallback(raw);
    }

    private RewrittenQuery parse(String raw, String content) {
        try {
            JsonNode root = objectMapper.readTree(content);
            String topic = textOrNull(root, "topicQuery");
            String body = textOrNull(root, "bodyQuery");
            String keywords = textOrNull(root, "keywords");
            if (!StringUtils.hasText(topic) && !StringUtils.hasText(body)) {
                return null;
            }
            if (!StringUtils.hasText(topic)) {
                topic = body;
            }
            if (!StringUtils.hasText(body)) {
                body = topic;
            }
            String fts = StringUtils.hasText(keywords) ? keywords : body;
            return new RewrittenQuery(raw, topic.trim(), body.trim(), fts.trim(), true);
        } catch (Exception e) {
            return null;
        }
    }

    private static RewrittenQuery ruleFallback(String raw) {
        String cleaned = CHAT_PREFIX.matcher(raw).replaceFirst("").trim();
        cleaned = TRAILING_NOISE.matcher(cleaned).replaceFirst("").trim();
        if (!StringUtils.hasText(cleaned)) {
            cleaned = raw;
        }
        return new RewrittenQuery(raw, cleaned, cleaned, cleaned, false);
    }

    private static String textOrNull(JsonNode root, String field) {
        if (root == null || !root.has(field) || root.get(field).isNull()) {
            return null;
        }
        String v = root.get(field).asText();
        return StringUtils.hasText(v) ? v.trim() : null;
    }

    private String loadPrompt() {
        try {
            return StreamUtils.copyToString(
                    new ClassPathResource("prompts/query_rewrite.md").getInputStream(),
                    StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "Product: {{productName}}\nQuery: {{query}}\nJSON: {\"topicQuery\":\"\",\"bodyQuery\":\"\",\"keywords\":\"\"}";
        }
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max);
    }

    public record RewrittenQuery(
            String originalQuery,
            String topicQuery,
            String bodyQuery,
            String ftsQuery,
            boolean llmRewritten
    ) {
        /** 不改写：topic/body/fts 均用原始 query。 */
        public static RewrittenQuery fallback(String raw) {
            String q = raw == null ? "" : raw;
            return new RewrittenQuery(q, q, q, q, false);
        }
    }
}
