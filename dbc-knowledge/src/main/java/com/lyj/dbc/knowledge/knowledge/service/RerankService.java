package com.lyj.dbc.knowledge.knowledge.service;

import com.lyj.dbc.knowledge.llm.client.LlmClient;
import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.llm.model.RerankHit;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

/**
 * 加权融合之后，用千问 text-rerank 对候选做交叉编码器重排。
 * 失败时保留融合顺序（fail-open）。
 */
@Service
public class RerankService {
    private static final Logger log = LoggerFactory.getLogger(RerankService.class);
    private static final int DOC_CHAR_LIMIT = 2000;

    private final LlmClient llmClient;
    private final LlmProperties llmProperties;

    public RerankService(LlmClient llmClient, LlmProperties llmProperties) {
        this.llmClient = llmClient;
        this.llmProperties = llmProperties;
    }

    public List<SearchHit> rerank(String query, List<SearchHit> hits) {
        if (hits == null || hits.size() <= 1 || !StringUtils.hasText(query)) {
            return hits;
        }
        if (!llmProperties.isEnabled() || !llmProperties.isRerankEnabled() || !hasRerankKey()) {
            return hits;
        }
        List<String> docs = new ArrayList<>(hits.size());
        for (SearchHit hit : hits) {
            docs.add(toDocument(hit));
        }
        try {
            List<RerankHit> ranks = llmClient.rerank(query.trim(), docs);
            List<SearchHit> ordered = applyRerankOrder(hits, ranks);
            log.info("knowledge rerank ok model={} in={} out={}",
                    llmProperties.getRerankModel(), hits.size(), ordered.size());
            return ordered;
        } catch (Exception e) {
            log.warn("knowledge rerank failed, keep hybrid order: {}", e.getMessage());
            return hits;
        }
    }

    public boolean enabled() {
        return llmProperties.isEnabled() && llmProperties.isRerankEnabled() && hasRerankKey();
    }

    private boolean hasRerankKey() {
        return StringUtils.hasText(llmProperties.getRerankApiKey())
                || StringUtils.hasText(llmProperties.getApiKey());
    }

    static String toDocument(SearchHit hit) {
        String title = hit.getTitle() == null ? "" : hit.getTitle().trim();
        String description = hit.getDescription() == null ? "" : hit.getDescription().trim();
        String bodySummary = hit.getBodySummary() == null ? "" : hit.getBodySummary().trim();
        StringBuilder sb = new StringBuilder();
        if (!title.isEmpty()) {
            sb.append(title);
        }
        if (!description.isEmpty() && !description.equals(title)) {
            if (!sb.isEmpty()) {
                sb.append('\n');
            }
            sb.append(description);
        }
        if (!bodySummary.isEmpty() && !bodySummary.equals(title) && !bodySummary.equals(description)) {
            if (!sb.isEmpty()) {
                sb.append('\n');
            }
            sb.append(bodySummary);
        }
        String text = sb.toString();
        if (text.length() <= DOC_CHAR_LIMIT) {
            return text;
        }
        return text.substring(0, DOC_CHAR_LIMIT);
    }

    static List<SearchHit> applyRerankOrder(List<SearchHit> hits, List<RerankHit> ranks) {
        if (hits == null || hits.isEmpty() || ranks == null || ranks.isEmpty()) {
            return hits;
        }
        boolean[] used = new boolean[hits.size()];
        List<SearchHit> out = new ArrayList<>(hits.size());
        for (RerankHit r : ranks) {
            int i = r.index();
            if (i < 0 || i >= hits.size() || used[i]) {
                continue;
            }
            SearchHit hit = hits.get(i);
            hit.setScore(r.score());
            out.add(hit);
            used[i] = true;
        }
        for (int i = 0; i < hits.size(); i++) {
            if (!used[i]) {
                out.add(hits.get(i));
            }
        }
        return out;
    }
}
