package com.lyj.dbc.knowledge.knowledge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.knowledge.llm.client.LlmClient;
import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.error.LlmException;
import com.lyj.dbc.knowledge.llm.model.ChatMessage;
import com.lyj.dbc.knowledge.llm.model.ChatRequest;
import com.lyj.dbc.knowledge.llm.model.ChatResponse;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.Slice;
import com.lyj.dbc.knowledge.knowledge.dto.SliceBatchSaveRequest;
import com.lyj.dbc.knowledge.knowledge.dto.SliceSaveItem;
import com.lyj.dbc.knowledge.knowledge.dto.SliceVo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

@Service
public class SliceSuggestService {
    private static final Logger log = LoggerFactory.getLogger(SliceSuggestService.class);

    /** Qwen3b-RagSemanticChunker 的固定系统提示：分组之间用「段」隔开。 */
    private static final String CHUNKER_SYSTEM = """
            Your job is to act as a semantic chunker.
            The goal is to separate the content into semantically relevant groupings.
            Each group must be delimited by the "段" character.""";

    private final LlmClient llmClient;
    private final LlmProperties llmProperties;
    private final DocumentService documentService;
    private final CategoryService categoryService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public SliceSuggestService(LlmClient llmClient,
                               LlmProperties llmProperties,
                               DocumentService documentService,
                               CategoryService categoryService) {
        this.llmClient = llmClient;
        this.llmProperties = llmProperties;
        this.documentService = documentService;
        this.categoryService = categoryService;
    }

    /**
     * @param sliceRule 调用方传入的切片规则话术；空则按正文结构做默认 AI 切片
     */
    @Transactional
    public List<SliceVo> suggestAndSave(Long documentId, boolean force, String sliceRule) {
        Document doc = documentService.require(documentId);

        List<Slice> existing = documentService.listSlices(documentId);
        if (!existing.isEmpty() && !force) {
            return existing.stream().map(this::toVo).toList();
        }

        List<SliceSaveItem> items;
        try {
            items = suggestByLlm(doc, sliceRule);
        } catch (Exception e) {
            log.warn("LLM suggest-slices failed, fallback to rules", e);
            items = suggestByRules(doc);
        }
        if (items.isEmpty()) {
            items = suggestByRules(doc);
        }

        SliceBatchSaveRequest req = new SliceBatchSaveRequest();
        req.setSlices(items);
        List<Slice> saved = documentService.saveSlices(documentId, req);
        return saved.stream().map(this::toVo).toList();
    }

    private List<SliceSaveItem> suggestByLlm(Document doc, String sliceRule) {
        String body = doc.getBody() == null ? "" : doc.getBody();
        if (body.length() > 12000) {
            body = body.substring(0, 12000);
        }
        String system = CHUNKER_SYSTEM;
        if (StringUtils.hasText(sliceRule)) {
            system = system + "\nAdditional caller rule:\n" + sliceRule.trim();
        }
        String user = "Segment this text:\n\n```text\n" + body + "\n```";
        String model = StringUtils.hasText(llmProperties.getSliceModel())
                ? llmProperties.getSliceModel().trim()
                : "Qwen3b-RagSemanticChunker";

        ChatResponse resp = llmClient.chat(ChatRequest.builder()
                .caller("memory-slice")
                .model(model)
                .temperature(0.1)
                .maxTokens(8192)
                .messages(List.of(
                        ChatMessage.system(system),
                        ChatMessage.user(user)
                ))
                .build());
        return parseModelOutput(resp.getContent(), doc);
    }

    /** 优先按「段」切开；若模型仍返回 slices JSON，则走原解析。 */
    private List<SliceSaveItem> parseModelOutput(String content, Document doc) {
        String raw = content == null ? "" : content.trim();
        if (raw.contains("\"slices\"")) {
            try {
                List<SliceSaveItem> json = parseSlices(raw);
                if (!json.isEmpty()) {
                    return json;
                }
            } catch (Exception e) {
                log.warn("slice json parse failed, try 段 delimiter", e);
            }
        }
        return parseDelimited(raw, doc);
    }

    private List<SliceSaveItem> parseDelimited(String content, Document doc) {
        String text = stripFence(content);
        if (!text.contains("段")) {
            return List.of();
        }
        String[] parts = text.split("段");
        List<SliceSaveItem> items = new ArrayList<>();
        int seq = 0;
        for (String part : parts) {
            String segment = part == null ? "" : part.trim();
            if (!StringUtils.hasText(segment) || isPreamble(segment)) {
                continue;
            }
            items.add(ruleItem(seq, sliceTitle(segment, seq), segment, doc.getCategoryId()));
            seq++;
        }
        return items;
    }

    private static String stripFence(String text) {
        String t = text == null ? "" : text.trim();
        if (t.startsWith("```")) {
            int nl = t.indexOf('\n');
            if (nl > 0) {
                t = t.substring(nl + 1);
            }
            int end = t.lastIndexOf("```");
            if (end >= 0) {
                t = t.substring(0, end);
            }
        }
        return t.trim();
    }

    private static boolean isPreamble(String segment) {
        String p = segment.toLowerCase();
        return p.startsWith("sure,")
                || p.contains("segmented using")
                || p.contains("here is the text");
    }

    private static String sliceTitle(String segment, int seq) {
        String first = segment.split("\n", 2)[0].trim();
        if (first.startsWith("#")) {
            first = first.replaceFirst("^#+\\s*", "").trim();
        }
        if (!StringUtils.hasText(first)) {
            return "切片 " + (seq + 1);
        }
        return first.length() > 40 ? first.substring(0, 40) : first;
    }

    private List<SliceSaveItem> parseSlices(String content) {
        try {
            JsonNode root = objectMapper.readTree(content);
            JsonNode arr = root.path("slices");
            if (!arr.isArray()) {
                arr = root.isArray() ? root : null;
            }
            if (arr == null) {
                return List.of();
            }
            List<SliceSaveItem> items = new ArrayList<>();
            int i = 0;
            for (JsonNode n : arr) {
                SliceSaveItem item = new SliceSaveItem();
                item.setSeqNo(i++);
                String title = n.path("title").asText("未命名切片");
                if (!StringUtils.hasText(title)) {
                    title = "未命名切片";
                }
                item.setTitle(title);
                String sliceBody = n.path("body").asText("");
                String description = textOrEmpty(n, "description");
                if (!StringUtils.hasText(description)) {
                    description = textOrEmpty(n, "summary");
                }
                if (!StringUtils.hasText(description)) {
                    description = nthNonBlankLine(sliceBody, 1, "");
                }
                String bodySummary = textOrEmpty(n, "bodySummary");
                if (!StringUtils.hasText(bodySummary)) {
                    bodySummary = textOrEmpty(n, "body_summary");
                }
                if (!StringUtils.hasText(bodySummary)) {
                    bodySummary = nthNonBlankLine(sliceBody, 2, "");
                }
                item.setDescription(description);
                item.setBodySummary(bodySummary);
                item.setBody(sliceBody);
                item.setOrientation(KnowledgeEnums.ORIENT_HORIZONTAL);
                if (n.has("categoryId") && !n.get("categoryId").isNull()) {
                    item.setCategoryId(n.get("categoryId").asLong());
                }
                List<String> tags = new ArrayList<>();
                if (n.path("techTags").isArray()) {
                    n.path("techTags").forEach(t -> tags.add(t.asText()));
                }
                item.setTechTags(tags);
                items.add(item);
            }
            return items;
        } catch (Exception e) {
            throw new LlmException("parse slice json failed: " + e.getMessage(), e);
        }
    }

    private static String textOrEmpty(JsonNode n, String field) {
        if (n == null || !n.has(field) || n.get(field).isNull()) {
            return "";
        }
        String v = n.path(field).asText("");
        return v == null ? "" : v.trim();
    }

    /** LLM 不可用时的兜底：按 Markdown 二级标题切，否则整篇一片。 */
    private List<SliceSaveItem> suggestByRules(Document doc) {
        String body = doc.getBody() == null ? "" : doc.getBody().trim();
        List<SliceSaveItem> items = new ArrayList<>();
        if (body.isEmpty()) {
            return items;
        }
        int seq = 0;
        if (body.contains("\n## ") || body.startsWith("## ")) {
            String[] parts = body.split("(?m)(?=^## )");
            for (String part : parts) {
                String p = part.trim();
                if (p.isEmpty()) {
                    continue;
                }
                String title = doc.getTitle();
                String content = p;
                if (p.startsWith("## ")) {
                    int nl = p.indexOf('\n');
                    title = nl > 0 ? p.substring(3, nl).trim() : p.substring(3).trim();
                    content = nl > 0 ? p.substring(nl + 1).trim() : "";
                }
                items.add(ruleItem(seq++, title, content, doc.getCategoryId()));
            }
        }
        if (items.isEmpty()) {
            items.add(ruleItem(0, doc.getTitle(), body, doc.getCategoryId()));
        }
        return items;
    }

    private static SliceSaveItem ruleItem(int seq, String title, String content, Long categoryId) {
        SliceSaveItem item = new SliceSaveItem();
        String resolvedTitle = title == null || title.isEmpty() ? "切片 " + (seq + 1) : title;
        item.setSeqNo(seq);
        item.setTitle(resolvedTitle);
        // 说明=第1个非空行；正文摘要=第2个非空行
        item.setDescription(nthNonBlankLine(content, 1, ""));
        item.setBodySummary(nthNonBlankLine(content, 2, ""));
        item.setBody(content == null ? "" : content);
        item.setOrientation(KnowledgeEnums.ORIENT_HORIZONTAL);
        item.setCategoryId(categoryId);
        return item;
    }

    /**
     * 取正文第 n 个非空行（1-based）；不足则回退 fallback。
     */
    private static String nthNonBlankLine(String content, int n, String fallback) {
        if (n < 1) {
            return fallback == null ? "" : fallback;
        }
        if (content != null) {
            int found = 0;
            for (String line : content.split("\n", -1)) {
                String trimmed = line == null ? "" : line.trim();
                if (!StringUtils.hasText(trimmed)) {
                    continue;
                }
                found++;
                if (found == n) {
                    return trimmed;
                }
            }
        }
        return fallback == null ? "" : fallback;
    }

    private SliceVo toVo(Slice s) {
        SliceVo vo = new SliceVo();
        vo.setId(s.getId());
        vo.setDocumentId(s.getDocumentId());
        vo.setSeqNo(s.getSeqNo());
        vo.setTitle(s.getTitle());
        vo.setDescription(s.getDescription());
        vo.setBodySummary(s.getBodySummary());
        vo.setBody(s.getBody());
        vo.setTechTags(s.getTechTags() == null ? List.of() : s.getTechTags());
        vo.setOrientation(s.getOrientation() == null ? KnowledgeEnums.ORIENT_HORIZONTAL : s.getOrientation());
        vo.setCategoryId(s.getCategoryId());
        vo.setCategoryPath(categoryService.pathLabel(s.getCategoryId()));
        vo.setStatus(s.getStatus());
        return vo;
    }
}
