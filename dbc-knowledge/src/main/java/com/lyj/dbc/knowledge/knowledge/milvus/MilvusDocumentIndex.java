package com.lyj.dbc.knowledge.knowledge.milvus;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import io.milvus.v2.client.MilvusClientV2;
import io.milvus.v2.common.DataType;
import io.milvus.v2.common.IndexParam;
import io.milvus.v2.service.collection.request.AddFieldReq;
import io.milvus.v2.service.collection.request.CreateCollectionReq;
import io.milvus.v2.service.collection.request.DescribeCollectionReq;
import io.milvus.v2.service.collection.request.DropCollectionReq;
import io.milvus.v2.service.collection.request.HasCollectionReq;
import io.milvus.v2.service.collection.request.LoadCollectionReq;
import io.milvus.v2.service.collection.response.DescribeCollectionResp;
import io.milvus.v2.service.vector.request.AnnSearchReq;
import io.milvus.v2.service.vector.request.DeleteReq;
import io.milvus.v2.service.vector.request.HybridSearchReq;
import io.milvus.v2.service.vector.request.UpsertReq;
import io.milvus.v2.service.vector.request.data.BaseVector;
import io.milvus.v2.service.vector.request.data.FloatVec;
import io.milvus.v2.service.vector.request.ranker.WeightedRanker;
import io.milvus.v2.service.vector.response.SearchResp;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 原文检索索引：标题向量 + 简介向量。
 */
@Component
@ConditionalOnBean(MilvusClientV2.class)
public class MilvusDocumentIndex {
    private static final Logger log = LoggerFactory.getLogger(MilvusDocumentIndex.class);
    private static final Gson GSON = new Gson();

    public static final String F_UNIT_ID = "unit_id";
    public static final String F_REF_ID = "ref_id";
    public static final String F_DOCUMENT_ID = "document_id";
    public static final String F_CATEGORY_ID = "category_id";
    public static final String F_PRODUCT_NAME = "product_name";
    public static final String F_KIND = "kind";
    public static final String F_STATUS = "status";
    public static final String F_TITLE = "title";
    public static final String F_SUMMARY = "summary";
    public static final String F_EMB_TITLE = "embedding_title";
    public static final String F_EMB_SUMMARY = "embedding_summary";

    private final MilvusClientV2 client;
    private final MilvusProperties props;

    public MilvusDocumentIndex(MilvusClientV2 client, MilvusProperties props) {
        this.client = client;
        this.props = props;
    }

    @PostConstruct
    public void ensureCollection() {
        String name = props.getDocumentCollection();
        Boolean exists = client.hasCollection(HasCollectionReq.builder().collectionName(name).build());
        if (Boolean.TRUE.equals(exists) && !isCurrentSchema(name)) {
            log.warn("Milvus document collection {} schema outdated, dropping for recreate", name);
            client.dropCollection(DropCollectionReq.builder().collectionName(name).build());
            exists = false;
        }
        if (!Boolean.TRUE.equals(exists)) {
            createCollection(name);
            log.info("Milvus document collection created: {}", name);
        }
        client.loadCollection(LoadCollectionReq.builder().collectionName(name).build());
        log.info("Milvus document collection ready: {}", name);
    }

    private boolean isCurrentSchema(String name) {
        try {
            DescribeCollectionResp desc = client.describeCollection(
                    DescribeCollectionReq.builder().collectionName(name).build());
            Set<String> fields = desc.getCollectionSchema().getFieldSchemaList().stream()
                    .map(CreateCollectionReq.FieldSchema::getName)
                    .collect(Collectors.toSet());
            return fields.contains(F_EMB_TITLE)
                    && fields.contains(F_EMB_SUMMARY)
                    && !fields.contains("embedding_doc_title")
                    && !fields.contains("text");
        } catch (Exception e) {
            log.warn("describe document collection failed, will recreate: {}", e.getMessage());
            return false;
        }
    }

    private void createCollection(String name) {
        int dim = props.getEmbedDim();
        CreateCollectionReq.CollectionSchema schema = CreateCollectionReq.CollectionSchema.builder().build();
        schema.addField(AddFieldReq.builder().fieldName(F_UNIT_ID).dataType(DataType.Int64).isPrimaryKey(true).autoID(false).build());
        schema.addField(AddFieldReq.builder().fieldName(F_REF_ID).dataType(DataType.Int64).build());
        schema.addField(AddFieldReq.builder().fieldName(F_DOCUMENT_ID).dataType(DataType.Int64).build());
        schema.addField(AddFieldReq.builder().fieldName(F_CATEGORY_ID).dataType(DataType.Int64).build());
        schema.addField(AddFieldReq.builder().fieldName(F_PRODUCT_NAME).dataType(DataType.VarChar).maxLength(128).build());
        schema.addField(AddFieldReq.builder().fieldName(F_KIND).dataType(DataType.VarChar).maxLength(16).build());
        schema.addField(AddFieldReq.builder().fieldName(F_STATUS).dataType(DataType.VarChar).maxLength(16).build());
        schema.addField(AddFieldReq.builder().fieldName(F_TITLE).dataType(DataType.VarChar).maxLength(256).build());
        schema.addField(AddFieldReq.builder().fieldName(F_SUMMARY).dataType(DataType.VarChar).maxLength(512).build());
        schema.addField(AddFieldReq.builder().fieldName(F_EMB_TITLE).dataType(DataType.FloatVector).dimension(dim).build());
        schema.addField(AddFieldReq.builder().fieldName(F_EMB_SUMMARY).dataType(DataType.FloatVector).dimension(dim).build());

        List<IndexParam> indexes = List.of(hnswIndex(F_EMB_TITLE), hnswIndex(F_EMB_SUMMARY));
        client.createCollection(CreateCollectionReq.builder()
                .collectionName(name)
                .collectionSchema(schema)
                .indexParams(indexes)
                .build());
    }

    private static IndexParam hnswIndex(String field) {
        return IndexParam.builder().fieldName(field).indexType(IndexParam.IndexType.HNSW)
                .metricType(IndexParam.MetricType.COSINE)
                .extraParams(Map.of("M", 16, "efConstruction", 200)).build();
    }

    public void upsertDocuments(List<DocumentVectorRow> rows) {
        if (rows == null || rows.isEmpty()) {
            return;
        }
        List<JsonObject> data = new ArrayList<>(rows.size());
        for (DocumentVectorRow row : rows) {
            JsonObject o = new JsonObject();
            o.addProperty(F_UNIT_ID, row.unitId());
            o.addProperty(F_REF_ID, row.refId());
            o.addProperty(F_DOCUMENT_ID, row.documentId());
            o.addProperty(F_CATEGORY_ID, nullToZero(row.categoryId()));
            o.addProperty(F_PRODUCT_NAME, nullToEmpty(row.productName()));
            o.addProperty(F_KIND, "DOCUMENT");
            o.addProperty(F_STATUS, "PUBLISHED");
            o.addProperty(F_TITLE, truncate(nullToEmpty(row.title()), 256));
            o.addProperty(F_SUMMARY, truncate(nullToEmpty(row.summary()), 512));
            o.add(F_EMB_TITLE, GSON.toJsonTree(toList(row.titleVec())));
            o.add(F_EMB_SUMMARY, GSON.toJsonTree(toList(row.summaryVec())));
            data.add(o);
        }
        client.upsert(UpsertReq.builder()
                .collectionName(props.getDocumentCollection())
                .data(data)
                .build());
        log.info("Milvus upsert documents count={}", rows.size());
    }

    public void deleteByDocumentId(long documentId) {
        client.delete(DeleteReq.builder()
                .collectionName(props.getDocumentCollection())
                .filter(F_DOCUMENT_ID + " == " + documentId)
                .build());
        log.info("Milvus delete document by documentId={}", documentId);
    }

    public List<SearchHit> search(float[] queryVec, String productName, Long categoryId, int topK) {
        return search(queryVec, productName, categoryId, null, topK);
    }

    public List<SearchHit> search(float[] queryVec, String productName, Long categoryId,
                                  List<Long> documentIds, int topK) {
        if (queryVec == null || queryVec.length == 0) {
            return List.of();
        }
        String filter = buildFilter(productName, categoryId, documentIds);
        int limit = Math.max(1, Math.min(topK, 50));
        List<BaseVector> q = List.of(new FloatVec(queryVec));
        List<AnnSearchReq> reqs = List.of(
                ann(F_EMB_TITLE, q, filter, limit),
                ann(F_EMB_SUMMARY, q, filter, limit)
        );
        SearchResp resp = client.hybridSearch(HybridSearchReq.builder()
                .collectionName(props.getDocumentCollection())
                .searchRequests(reqs)
                .ranker(new WeightedRanker(List.of(0.70f, 0.30f)))
                .topK(limit)
                .outFields(List.of(F_UNIT_ID, F_REF_ID, F_DOCUMENT_ID, F_CATEGORY_ID,
                        F_PRODUCT_NAME, F_TITLE, F_SUMMARY, F_KIND, F_STATUS))
                .build());
        return toHits(resp);
    }

    private static AnnSearchReq ann(String field, List<BaseVector> q, String filter, int limit) {
        return AnnSearchReq.builder()
                .vectorFieldName(field)
                .vectors(q)
                .topK(limit)
                .expr(filter)
                .params("{\"ef\":64}")
                .build();
    }

    private String buildFilter(String productName, Long categoryId, List<Long> documentIds) {
        StringBuilder sb = new StringBuilder();
        sb.append(F_STATUS).append(" == \"PUBLISHED\" && ")
                .append(F_KIND).append(" == \"DOCUMENT\"");
        if (StringUtils.hasText(productName)) {
            sb.append(" && ").append(F_PRODUCT_NAME).append(" == \"")
                    .append(escape(productName.trim())).append('"');
        }
        if (categoryId != null) {
            sb.append(" && ").append(F_CATEGORY_ID).append(" == ").append(categoryId);
        }
        MilvusSliceIndex.appendDocumentIdsFilter(sb, documentIds);
        return sb.toString();
    }

    private static List<SearchHit> toHits(SearchResp resp) {
        List<SearchHit> hits = new ArrayList<>();
        if (resp.getSearchResults() == null || resp.getSearchResults().isEmpty()) {
            return hits;
        }
        for (SearchResp.SearchResult result : resp.getSearchResults().get(0)) {
            Map<String, Object> entity = result.getEntity();
            SearchHit hit = new SearchHit();
            hit.setId(asLong(entity.get(F_UNIT_ID)));
            hit.setRefId(asLong(entity.get(F_REF_ID)));
            Long docId = asLong(entity.get(F_DOCUMENT_ID));
            hit.setDocumentId(docId != null && docId > 0 ? docId : asLong(entity.get(F_REF_ID)));
            hit.setCategoryId(zeroToNull(asLong(entity.get(F_CATEGORY_ID))));
            hit.setTitle(asString(entity.get(F_TITLE)));
            hit.setDescription(asString(entity.get(F_SUMMARY)));
            hit.setBodySummary("");
            hit.setKind(asString(entity.get(F_KIND)));
            hit.setStatus(asString(entity.get(F_STATUS)));
            hit.setScore(result.getScore() == null ? 0.0 : result.getScore().doubleValue());
            hits.add(hit);
        }
        return hits;
    }

    private static String escape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static long nullToZero(Long v) {
        return v == null ? 0L : v;
    }

    private static Long zeroToNull(Long v) {
        return v == null || v == 0L ? null : v;
    }

    private static String nullToEmpty(String s) {
        return s == null ? "" : s;
    }

    /** Milvus VarChar maxLength 按 UTF-8 字节计。 */
    static String truncate(String s, int maxBytes) {
        return MilvusSliceIndex.truncate(s, maxBytes);
    }

    private static List<Float> toList(float[] vec) {
        if (vec == null) {
            return List.of();
        }
        List<Float> list = new ArrayList<>(vec.length);
        for (float v : vec) {
            list.add(v);
        }
        return list;
    }

    private static Long asLong(Object o) {
        if (o == null) {
            return null;
        }
        if (o instanceof Number n) {
            return n.longValue();
        }
        return Long.parseLong(o.toString());
    }

    private static String asString(Object o) {
        return o == null ? null : o.toString();
    }

    public record DocumentVectorRow(
            long unitId,
            long refId,
            long documentId,
            Long categoryId,
            String productName,
            String title,
            String summary,
            float[] titleVec,
            float[] summaryVec
    ) {
    }
}
