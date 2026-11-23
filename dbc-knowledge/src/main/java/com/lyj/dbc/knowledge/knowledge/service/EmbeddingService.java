package com.lyj.dbc.knowledge.knowledge.service;

import com.lyj.dbc.knowledge.llm.client.LlmClient;
import com.lyj.dbc.knowledge.llm.config.LlmProperties;
import com.lyj.dbc.knowledge.knowledge.domain.Document;
import com.lyj.dbc.knowledge.knowledge.domain.KnowledgeEnums;
import com.lyj.dbc.knowledge.knowledge.domain.UnitIndex;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusDocumentIndex;
import com.lyj.dbc.knowledge.knowledge.milvus.MilvusSliceIndex;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class EmbeddingService {
    private static final Logger log = LoggerFactory.getLogger(EmbeddingService.class);

    private final LlmClient llmClient;
    private final LlmProperties llmProperties;

    public EmbeddingService(LlmClient llmClient, LlmProperties llmProperties) {
        this.llmClient = llmClient;
        this.llmProperties = llmProperties;
    }

    /** 原文：标题向量 + 简介向量（简介空则复用标题向量） */
    public List<MilvusDocumentIndex.DocumentVectorRow> buildDocumentRows(Document doc, List<UnitIndex> docUnits) {
        List<MilvusDocumentIndex.DocumentVectorRow> rows = new ArrayList<>();
        if (doc == null || docUnits == null || docUnits.isEmpty()) {
            return rows;
        }
        String title = StringUtils.hasText(doc.getTitle()) ? doc.getTitle().trim() : "未命名原文";
        String summary = doc.getSummary() == null ? "" : doc.getSummary().trim();
        String summaryForEmbed = StringUtils.hasText(summary) ? summary : title;

        Map<String, Integer> index = new LinkedHashMap<>();
        List<String> inputs = new ArrayList<>(2);
        index.put("title", inputs.size());
        inputs.add(title);
        if (!summaryForEmbed.equals(title)) {
            index.put("summary", inputs.size());
            inputs.add(summaryForEmbed);
        }
        List<float[]> vecs = llmClient.embed(inputs);
        float[] titleVec = fitDim(vecs.get(index.get("title")));
        float[] summaryVec = index.containsKey("summary")
                ? fitDim(vecs.get(index.get("summary")))
                : titleVec;

        for (UnitIndex unit : docUnits) {
            if (unit == null || !KnowledgeEnums.KIND_DOCUMENT.equalsIgnoreCase(unit.getKind())) {
                continue;
            }
            rows.add(new MilvusDocumentIndex.DocumentVectorRow(
                    unit.getId(),
                    unit.getRefId(),
                    unit.getRefId(),
                    unit.getCategoryId(),
                    doc.getProductName(),
                    title,
                    summary,
                    titleVec,
                    summaryVec
            ));
        }
        log.info("built milvus document rows documentId={} count={}", doc.getId(), rows.size());
        return rows;
    }

    /** 切片：标题 / 说明 / 正文摘要稠密；正文仅进 BM25 */
    public List<MilvusSliceIndex.SliceVectorRow> buildSliceRows(Document doc, List<UnitIndex> slices) {
        List<MilvusSliceIndex.SliceVectorRow> rows = new ArrayList<>();
        if (slices == null || slices.isEmpty()) {
            return rows;
        }
        String productName = doc == null ? null : doc.getProductName();
        String documentTitle = doc == null || !StringUtils.hasText(doc.getTitle())
                ? "未命名原文" : doc.getTitle().trim();

        for (UnitIndex unit : slices) {
            if (unit == null || !KnowledgeEnums.KIND_SLICE.equalsIgnoreCase(unit.getKind())) {
                continue;
            }
            String sliceTitle = unit.getTitle() == null ? "" : unit.getTitle().trim();
            String description = unit.getDescription() == null ? "" : unit.getDescription().trim();
            String bodySummary = unit.getBodySummary() == null ? "" : unit.getBodySummary().trim();
            String bodyText = unit.getBody() == null ? "" : unit.getBody().trim();
            if (bodyText.length() > 8000) {
                bodyText = bodyText.substring(0, 8000);
            }
            if (!StringUtils.hasText(sliceTitle)
                    && !StringUtils.hasText(description)
                    && !StringUtils.hasText(bodySummary)
                    && !StringUtils.hasText(bodyText)) {
                continue;
            }
            String titleForEmbed = StringUtils.hasText(sliceTitle) ? sliceTitle : documentTitle;
            String descForEmbed = StringUtils.hasText(description) ? description : titleForEmbed;
            String bodySumForEmbed = StringUtils.hasText(bodySummary) ? bodySummary : titleForEmbed;

            Map<String, Integer> index = new LinkedHashMap<>();
            List<String> inputs = new ArrayList<>(3);
            index.put("title", inputs.size());
            inputs.add(titleForEmbed);
            if (!descForEmbed.equals(titleForEmbed)) {
                index.put("description", inputs.size());
                inputs.add(descForEmbed);
            }
            if (!bodySumForEmbed.equals(titleForEmbed) && !bodySumForEmbed.equals(descForEmbed)) {
                index.put("bodySummary", inputs.size());
                inputs.add(bodySumForEmbed);
            } else if (bodySumForEmbed.equals(descForEmbed) && index.containsKey("description")) {
                // reuse description vec below
            } else if (!bodySumForEmbed.equals(titleForEmbed)) {
                index.put("bodySummary", inputs.size());
                inputs.add(bodySumForEmbed);
            }
            List<float[]> vecs = llmClient.embed(inputs);
            float[] titleVec = fitDim(vecs.get(index.get("title")));
            float[] descriptionVec = index.containsKey("description")
                    ? fitDim(vecs.get(index.get("description")))
                    : titleVec;
            float[] bodySummaryVec;
            if (index.containsKey("bodySummary")) {
                bodySummaryVec = fitDim(vecs.get(index.get("bodySummary")));
            } else if (bodySumForEmbed.equals(descForEmbed)) {
                bodySummaryVec = descriptionVec;
            } else {
                bodySummaryVec = titleVec;
            }

            rows.add(new MilvusSliceIndex.SliceVectorRow(
                    unit.getId(),
                    unit.getRefId(),
                    unit.getDocumentId(),
                    unit.getCategoryId(),
                    productName,
                    documentTitle,
                    sliceTitle,
                    description,
                    bodySummary,
                    bodyText,
                    titleVec,
                    descriptionVec,
                    bodySummaryVec
            ));
        }
        log.info("built milvus slice rows documentId={} count={}", doc == null ? null : doc.getId(), rows.size());
        return rows;
    }

    public float[] embedSearchQuery(String topicQuery) {
        String q = topicQuery == null ? "" : topicQuery.trim();
        if (!StringUtils.hasText(q)) {
            q = " ";
        }
        return fitDim(llmClient.embed(q));
    }

    private float[] fitDim(float[] vec) {
        int dim = llmProperties.getEmbedDim();
        if (vec.length == dim) {
            return vec;
        }
        float[] resized = new float[dim];
        System.arraycopy(vec, 0, resized, 0, Math.min(vec.length, dim));
        return resized;
    }
}
