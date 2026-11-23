package com.lyj.dbc.knowledge.knowledge.milvus;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.lyj.dbc.knowledge.knowledge.dto.SearchHit;
import io.milvus.common.clientenum.FunctionType;
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
import io.milvus.v2.service.vector.request.data.EmbeddedText;
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
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 切片检索索引：标题 / 说明 / 正文摘要稠密向量 + 正文 BM25。
 */
@Component
@ConditionalOnBean(MilvusClientV2.class)
public class MilvusSliceIndex {
    private static final Logger log = LoggerFactory.getLogger(MilvusSliceIndex.class);
    private static final Gson GSON = new Gson();

    public static final String F_UNIT_ID = "unit_id";
    public static final String F_REF_ID = "ref_id";
    public static final String F_DOCUMENT_ID = "document_id";
    public static final String F_CATEGORY_ID = "category_id";
    public static final String F_PRODUCT_NAME = "product_name";
    public static final String F_DOCUMENT_TITLE = "document_title";
    public static final String F_KIND = "kind";
    public static final String F_STATUS = "status";
    public static final String F_TITLE = "title";
    public static final String F_DESCRIPTION = "description";
    public static final String F_BODY_SUMMARY = "body_summary";
    public static final String F_TEXT = "text";
    public static final String F_EMB_TITLE = "embedding_title";
    public static final String F_EMB_DESCRIPTION = "embedding_description";
    public static final String F_EMB_BODY_SUMMARY = "embedding_body_summary";
    public static final String F_SPARSE = "text_sparse";

    /** 与 PG VARCHAR(2048) 对齐；Milvus VarChar maxLength 按 UTF-8 字节，8192 可覆盖满宽中文。 */
    static final int MAX_LEN_DESCRIPTION = 8192;
    static final int MAX_LEN_BODY_SUMMARY = 8192;
    static final int MAX_LEN_TITLE = 256;
    static final int MAX_LEN_TEXT = 65535;

    private final MilvusClientV2 client;
    private final MilvusProperties props;

    public MilvusSliceIndex(MilvusClientV2 client, MilvusProperties props) {
        this.client = client;
        this.props = props;
    }

    @PostConstruct
    public void ensureCollection() {
        String name = props.getCollection();
        Boolean exists = client.hasCollection(HasCollectionReq.builder().collectionName(name).build());
        if (Boolean.TRUE.equals(exists) && !isCurrentSchema(name)) {
            log.warn("Milvus slice collection {} schema outdated, dropping for recreate", name);
            client.dropCollection(DropCollectionReq.builder().collectionName(name).build());
            exists = false;
        }
        if (!Boolean.TRUE.equals(exists)) {
            createCollection(name);
            log.info("Milvus slice collection created: {}", name);
        }
        client.loadCollection(LoadCollectionReq.builder().collectionName(name).build());
        log.info("Milvus slice collection ready: {}", name);
    }

    private boolean isCurrentSchema(String name) {
        try {
            DescribeCollectionResp desc = client.describeCollection(
                    DescribeCollectionReq.builder().collectionName(name).build());
            CreateCollectionReq.CollectionSchema schema = desc.getCollectionSchema();
            Set<String> fields = schema.getFieldSchemaList().stream()
                    .map(CreateCollectionReq.FieldSchema::getName)
                    .collect(Collectors.toSet());
            CreateCollectionReq.FieldSchema description = schema.getField(F_DESCRIPTION);
            CreateCollectionReq.FieldSchema bodySummary = schema.getField(F_BODY_SUMMARY);
            return fields.contains(F_EMB_TITLE)
                    && fields.contains(F_EMB_DESCRIPTION)
                    && fields.contains(F_EMB_BODY_SUMMARY)
                    && fields.contains(F_DESCRIPTION)
                    && fields.contains(F_BODY_SUMMARY)
                    && fields.contains(F_SPARSE)
                    && !fields.contains("embedding_summary")
                    && !fields.contains("summary")
                    && description != null
                    && description.getMaxLength() != null
                    && description.getMaxLength() >= MAX_LEN_DESCRIPTION
                    && bodySummary != null
                    && bodySummary.getMaxLength() != null
                    && bodySummary.getMaxLength() >= MAX_LEN_BODY_SUMMARY;
        } catch (Exception e) {
            log.warn("describe slice collection failed, will recreate: {}", e.getMessage());
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
        schema.addField(AddFieldReq.builder().fieldName(F_DOCUMENT_TITLE).dataType(DataType.VarChar).maxLength(256).build());
        schema.addField(AddFieldReq.builder().fieldName(F_KIND).dataType(DataType.VarChar).maxLength(16).build());
        schema.addField(AddFieldReq.builder().fieldName(F_STATUS).dataType(DataType.VarChar).maxLength(16).build());
        schema.addField(AddFieldReq.builder().fieldName(F_TITLE).dataType(DataType.VarChar).maxLength(MAX_LEN_TITLE).build());
        schema.addField(AddFieldReq.builder().fieldName(F_DESCRIPTION).dataType(DataType.VarChar).maxLength(MAX_LEN_DESCRIPTION).build());
        schema.addField(AddFieldReq.builder().fieldName(F_BODY_SUMMARY).dataType(DataType.VarChar).maxLength(MAX_LEN_BODY_SUMMARY).build());
        schema.addField(AddFieldReq.builder()
                .fieldName(F_TEXT)
                .dataType(DataType.VarChar)
                .maxLength(MAX_LEN_TEXT)
                .enableAnalyzer(true)
                .analyzerParams(Map.of("type", "chinese"))
                .build());
        schema.addField(AddFieldReq.builder().fieldName(F_EMB_TITLE).dataType(DataType.FloatVector).dimension(dim).build());
        schema.addField(AddFieldReq.builder().fieldName(F_EMB_DESCRIPTION).dataType(DataType.FloatVector).dimension(dim).build());
        schema.addField(AddFieldReq.builder().fieldName(F_EMB_BODY_SUMMARY).dataType(DataType.FloatVector).dimension(dim).build());
        schema.addField(AddFieldReq.builder().fieldName(F_SPARSE).dataType(DataType.SparseFloatVector).build());
        schema.addFunction(CreateCollectionReq.Function.builder()
                .functionType(FunctionType.BM25)
                .name("text_bm25")
                .inputFieldNames(List.of(F_TEXT))
                .outputFieldNames(List.of(F_SPARSE))
                .build());

        List<IndexParam> indexes = List.of(
                hnswIndex(F_EMB_TITLE),
                hnswIndex(F_EMB_DESCRIPTION),
                hnswIndex(F_EMB_BODY_SUMMARY),
                IndexParam.builder().fieldName(F_SPARSE).indexType(IndexParam.IndexType.SPARSE_INVERTED_INDEX)
                        .metricType(IndexParam.MetricType.BM25).build()
        );

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

    public void upsertSlices(List<SliceVectorRow> rows) {
        if (rows == null || rows.isEmpty()) {
            return;
        }
        List<JsonObject> data = new ArrayList<>(rows.size());
        for (SliceVectorRow row : rows) {
            JsonObject o = new JsonObject();
            o.addProperty(F_UNIT_ID, row.unitId());
            o.addProperty(F_REF_ID, row.refId());
            o.addProperty(F_DOCUMENT_ID, nullToZero(row.documentId()));
            o.addProperty(F_CATEGORY_ID, nullToZero(row.categoryId()));
            o.addProperty(F_PRODUCT_NAME, nullToEmpty(row.productName()));
            o.addProperty(F_DOCUMENT_TITLE, truncate(nullToEmpty(row.documentTitle()), MAX_LEN_TITLE));
            o.addProperty(F_KIND, "SLICE");
            o.addProperty(F_STATUS, "PUBLISHED");
            o.addProperty(F_TITLE, truncate(nullToEmpty(row.sliceTitle()), MAX_LEN_TITLE));
            // description / body_summary：按字段上限入库，不做内容截断
            o.addProperty(F_DESCRIPTION, nullToEmpty(row.description()));
            o.addProperty(F_BODY_SUMMARY, nullToEmpty(row.bodySummary()));
            o.addProperty(F_TEXT, truncate(nullToEmpty(row.bodyText()), MAX_LEN_TEXT));
            o.add(F_EMB_TITLE, GSON.toJsonTree(toList(row.titleVec())));
            o.add(F_EMB_DESCRIPTION, GSON.toJsonTree(toList(row.descriptionVec())));
            o.add(F_EMB_BODY_SUMMARY, GSON.toJsonTree(toList(row.bodySummaryVec())));
            data.add(o);
        }
        client.upsert(UpsertReq.builder()
                .collectionName(props.getCollection())
                .data(data)
                .build());
        log.info("Milvus upsert slices count={}", rows.size());
    }

    public void deleteByDocumentId(long documentId) {
        client.delete(DeleteReq.builder()
                .collectionName(props.getCollection())
                .filter(F_DOCUMENT_ID + " == " + documentId)
                .build());
        log.info("Milvus delete slices by documentId={}", documentId);
    }

    public List<SearchHit> hybridSearch(float[] queryVec, String ftsQuery,
                                        String productName, Long categoryId, int topK) {
        return hybridSearch(queryVec, ftsQuery, productName, categoryId, null, topK);
    }

    /** 同一 dense 向量同时打 title / description / body_summary，再加正文 BM25。 */
    public List<SearchHit> hybridSearch(float[] queryVec, String ftsQuery,
                                        String productName, Long categoryId,
                                        List<Long> documentIds, int topK) {
        return hybridSearch(queryVec, queryVec, queryVec, ftsQuery, productName, categoryId, documentIds, topK);
    }

    /**
     * 分字段检索后加权融合：
     * <ul>
     *   <li>titleVec → embedding_title</li>
     *   <li>descriptionVec → embedding_description</li>
     *   <li>bodySummaryVec → embedding_body_summary</li>
     *   <li>ftsQuery → 正文 BM25</li>
     * </ul>
     */
    public List<SearchHit> hybridSearch(float[] titleVec, float[] descriptionVec, float[] bodySummaryVec,
                                        String ftsQuery,
                                        String productName, Long categoryId,
                                        List<Long> documentIds, int topK) {
        boolean hasTitle = titleVec != null && titleVec.length > 0;
        boolean hasDesc = descriptionVec != null && descriptionVec.length > 0;
        boolean hasBodySum = bodySummaryVec != null && bodySummaryVec.length > 0;
        boolean hasFts = StringUtils.hasText(ftsQuery);
        if (!hasTitle && !hasDesc && !hasBodySum && !hasFts) {
            return List.of();
        }
        String filter = buildFilter(productName, categoryId, documentIds);
        int limit = Math.max(1, Math.min(topK, 50));

        List<AnnSearchReq> reqs = new ArrayList<>();
        List<Float> rawWeights = new ArrayList<>();
        if (hasTitle) {
            reqs.add(ann(F_EMB_TITLE, List.of(new FloatVec(titleVec)), filter, limit));
            rawWeights.add(0.35f);
        }
        if (hasDesc) {
            reqs.add(ann(F_EMB_DESCRIPTION, List.of(new FloatVec(descriptionVec)), filter, limit));
            rawWeights.add(0.30f);
        }
        if (hasBodySum) {
            reqs.add(ann(F_EMB_BODY_SUMMARY, List.of(new FloatVec(bodySummaryVec)), filter, limit));
            rawWeights.add(0.20f);
        }
        if (hasFts) {
            reqs.add(AnnSearchReq.builder()
                    .vectorFieldName(F_SPARSE)
                    .vectors(Collections.singletonList(new EmbeddedText(ftsQuery.trim())))
                    .topK(limit)
                    .expr(filter)
                    .build());
            rawWeights.add(0.15f);
        }
        List<Float> weights = normalizeWeights(rawWeights);

        SearchResp resp = client.hybridSearch(HybridSearchReq.builder()
                .collectionName(props.getCollection())
                .searchRequests(reqs)
                .ranker(new WeightedRanker(weights))
                .topK(limit)
                .outFields(List.of(F_UNIT_ID, F_REF_ID, F_DOCUMENT_ID, F_CATEGORY_ID,
                        F_PRODUCT_NAME, F_DOCUMENT_TITLE, F_TITLE, F_DESCRIPTION, F_BODY_SUMMARY,
                        F_KIND, F_STATUS))
                .build());

        List<SearchHit> hits = new ArrayList<>();
        if (resp.getSearchResults() == null || resp.getSearchResults().isEmpty()) {
            return hits;
        }
        for (SearchResp.SearchResult result : resp.getSearchResults().get(0)) {
            Map<String, Object> entity = result.getEntity();
            SearchHit hit = new SearchHit();
            hit.setId(asLong(entity.get(F_UNIT_ID)));
            hit.setRefId(asLong(entity.get(F_REF_ID)));
            hit.setDocumentId(asLong(entity.get(F_DOCUMENT_ID)));
            hit.setCategoryId(zeroToNull(asLong(entity.get(F_CATEGORY_ID))));
            hit.setTitle(asString(entity.get(F_TITLE)));
            hit.setDescription(asString(entity.get(F_DESCRIPTION)));
            hit.setBodySummary(asString(entity.get(F_BODY_SUMMARY)));
            hit.setKind(asString(entity.get(F_KIND)));
            hit.setStatus(asString(entity.get(F_STATUS)));
            hit.setScore(result.getScore() == null ? 0.0 : result.getScore().doubleValue());
            hits.add(hit);
        }
        return hits;
    }

    /** 按默认占比缩放，使在场权重之和为 1。 */
    static List<Float> normalizeWeights(List<Float> raw) {
        if (raw == null || raw.isEmpty()) {
            return List.of();
        }
        float sum = 0f;
        for (Float w : raw) {
            sum += w == null ? 0f : w;
        }
        if (sum <= 0f) {
            float eq = 1f / raw.size();
            List<Float> out = new ArrayList<>(raw.size());
            for (int i = 0; i < raw.size(); i++) {
                out.add(eq);
            }
            return out;
        }
        List<Float> out = new ArrayList<>(raw.size());
        for (Float w : raw) {
            out.add((w == null ? 0f : w) / sum);
        }
        return out;
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
                .append(F_KIND).append(" == \"SLICE\"");
        if (StringUtils.hasText(productName)) {
            sb.append(" && ").append(F_PRODUCT_NAME).append(" == \"")
                    .append(escape(productName.trim())).append('"');
        }
        if (categoryId != null) {
            sb.append(" && ").append(F_CATEGORY_ID).append(" == ").append(categoryId);
        }
        appendDocumentIdsFilter(sb, documentIds);
        return sb.toString();
    }

    public static void appendDocumentIdsFilter(StringBuilder sb, List<Long> documentIds) {
        if (documentIds == null || documentIds.isEmpty()) {
            return;
        }
        sb.append(" && ").append(F_DOCUMENT_ID).append(" in [");
        for (int i = 0; i < documentIds.size(); i++) {
            if (i > 0) {
                sb.append(", ");
            }
            sb.append(documentIds.get(i));
        }
        sb.append(']');
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

    /**
     * Milvus VarChar maxLength 按 UTF-8 字节计；按码点截断到不超过 maxBytes。
     */
    static String truncate(String s, int maxBytes) {
        if (s == null || s.isEmpty() || maxBytes <= 0) {
            return s == null ? "" : s;
        }
        int byteCount = 0;
        int i = 0;
        while (i < s.length()) {
            int cp = s.codePointAt(i);
            int cpBytes = utf8Bytes(cp);
            if (byteCount + cpBytes > maxBytes) {
                break;
            }
            byteCount += cpBytes;
            i += Character.charCount(cp);
        }
        return i >= s.length() ? s : s.substring(0, i);
    }

    private static int utf8Bytes(int codePoint) {
        if (codePoint <= 0x7F) {
            return 1;
        }
        if (codePoint <= 0x7FF) {
            return 2;
        }
        if (codePoint <= 0xFFFF) {
            return 3;
        }
        return 4;
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

    public record SliceVectorRow(
            long unitId,
            long refId,
            Long documentId,
            Long categoryId,
            String productName,
            String documentTitle,
            String sliceTitle,
            String description,
            String bodySummary,
            String bodyText,
            float[] titleVec,
            float[] descriptionVec,
            float[] bodySummaryVec
    ) {
    }
}
