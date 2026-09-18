package com.lyj.dbc.audit.es;

import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import com.lyj.dbc.audit.common.BizException;
import com.lyj.dbc.audit.common.PageResult;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.data.elasticsearch.core.mapping.IndexCoordinates;
import org.springframework.data.elasticsearch.core.query.IndexQuery;
import org.springframework.data.elasticsearch.core.query.IndexQueryBuilder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * 审计文档索引与检索（Spring Data ElasticsearchOperations）。
 */
@Service
public class AuditEsService {

    private final ElasticsearchOperations elasticsearchOperations;
    private final AuditIndexNames indexNames;

    public AuditEsService(ElasticsearchOperations elasticsearchOperations, AuditIndexNames indexNames) {
        this.elasticsearchOperations = elasticsearchOperations;
        this.indexNames = indexNames;
    }

    /**
     * 按 eventId 幂等写入；返回写入的索引名。
     */
    public String index(AuditDocument doc) {
        if (doc == null || doc.getEventId() == null || doc.getEventId().isBlank()) {
            throw BizException.badRequest("eventId 不能为空");
        }
        String category = doc.getCategory() == null ? "" : doc.getCategory().trim().toUpperCase();
        Instant when = parseOccurredAt(doc.getOccurredAt());
        String index = "SQL".equals(category)
                ? indexNames.sqlIndex(when)
                : indexNames.bizIndex(when);

        IndexQuery query = new IndexQueryBuilder()
                .withId(doc.getEventId())
                .withObject(doc)
                .build();
        try {
            elasticsearchOperations.index(query, IndexCoordinates.of(index));
        } catch (Exception ex) {
            throw translateEs(ex);
        }
        return index;
    }
    public AuditDocument getBizById(String eventId) {
        return getById(eventId, indexNames.bizSearchPattern());
    }

    public AuditDocument getSqlById(String eventId) {
        return getById(eventId, indexNames.sqlSearchPattern());
    }

    public PageResult<AuditDocument> searchBiz(int page, int size,
                                               Instant from, Instant to,
                                               String operatorUsername, String module,
                                               String action, String result, String keyword) {
        BoolQuery.Builder bool = new BoolQuery.Builder();
        bool.filter(f -> f.term(t -> t.field("category").value("BIZ")));
        addTimeRange(bool, from, to);
        addTermIfPresent(bool, "operatorUsername", operatorUsername);
        addTermIfPresent(bool, "module", module);
        addTermIfPresent(bool, "action", action);
        addTermIfPresent(bool, "result", result);
        if (keyword != null && !keyword.isBlank()) {
            String kw = keyword.trim();
            bool.must(m -> m.bool(b -> b
                    .should(s -> s.wildcard(w -> w.field("failReason").value("*" + escapeWildcard(kw) + "*")))
                    .should(s -> s.wildcard(w -> w.field("resourceId").value("*" + escapeWildcard(kw) + "*")))
                    .should(s -> s.wildcard(w -> w.field("module").value("*" + escapeWildcard(kw) + "*")))
                    .minimumShouldMatch("1")
            ));
        }
        return search(bool.build()._toQuery(), page, size, indexNames.bizSearchPattern());
    }

    public PageResult<AuditDocument> searchSql(int page, int size,
                                               Instant from, Instant to,
                                               String operatorUsername, Long workspaceId,
                                               Long connectionId, String status, String sqlKeyword) {
        BoolQuery.Builder bool = new BoolQuery.Builder();
        bool.filter(f -> f.term(t -> t.field("category").value("SQL")));
        addTimeRange(bool, from, to);
        addTermIfPresent(bool, "operatorUsername", operatorUsername);
        addTermIfPresent(bool, "status", status);
        if (workspaceId != null) {
            bool.filter(f -> f.term(t -> t.field("workspaceId").value(workspaceId)));
        }
        if (connectionId != null) {
            bool.filter(f -> f.term(t -> t.field("connectionId").value(connectionId)));
        }
        if (sqlKeyword != null && !sqlKeyword.isBlank()) {
            String kw = sqlKeyword.trim();
            bool.must(m -> m.wildcard(w -> w.field("sqlText").value("*" + escapeWildcard(kw) + "*")));
        }
        return search(bool.build()._toQuery(), page, size, indexNames.sqlSearchPattern());
    }

    /**
     * 按 eventId 检索。不能用 {@code get(id, pattern-*)}：ES Get API 不支持通配索引名，
     * 会抛 {@code NoSuchIndexException: Index …-* not found}。
     */
    private AuditDocument getById(String eventId, String indexPattern) {
        if (eventId == null || eventId.isBlank()) {
            throw BizException.badRequest("eventId 不能为空");
        }
        NativeQuery nativeQuery = NativeQuery.builder()
                .withQuery(q -> q.ids(i -> i.values(eventId.trim())))
                .withMaxResults(1)
                .build();
        try {
            SearchHits<AuditDocument> hits = elasticsearchOperations.search(
                    nativeQuery, AuditDocument.class, IndexCoordinates.of(indexPattern));
            if (hits.isEmpty()) {
                throw BizException.notFound("审计事件不存在: " + eventId);
            }
            return hits.getSearchHit(0).getContent();
        } catch (BizException ex) {
            throw ex;
        } catch (Exception ex) {
            if (isIndexMissing(ex)) {
                throw BizException.notFound("审计事件不存在: " + eventId);
            }
            throw translateEs(ex);
        }
    }

    private PageResult<AuditDocument> search(Query query, int page, int size, String indexPattern) {
        int p = Math.max(page, 1);
        int s = Math.min(Math.max(size, 1), 200);
        NativeQuery nativeQuery = NativeQuery.builder()
                .withQuery(query)
                .withPageable(PageRequest.of(p - 1, s))
                .withSort(so -> so.field(f -> f.field("occurredAt").order(SortOrder.Desc)))
                .build();
        try {
            SearchHits<AuditDocument> hits = elasticsearchOperations.search(
                    nativeQuery, AuditDocument.class, IndexCoordinates.of(indexPattern));
            List<AuditDocument> records = new ArrayList<>(hits.getSearchHits().size());
            for (SearchHit<AuditDocument> hit : hits) {
                records.add(hit.getContent());
            }
            return new PageResult<>(records, hits.getTotalHits(), p, s);
        } catch (Exception ex) {
            // 索引尚未创建时返回空页，避免查询 API 500
            if (isIndexMissing(ex)) {
                return new PageResult<>(List.of(), 0, p, s);
            }
            throw translateEs(ex);
        }
    }

    private static Instant parseOccurredAt(String raw) {
        if (raw == null || raw.isBlank()) {
            return Instant.now();
        }
        try {
            return Instant.parse(raw.trim());
        } catch (Exception e) {
            return Instant.now();
        }
    }

    private static void addTimeRange(BoolQuery.Builder bool, Instant from, Instant to) {
        if (from == null && to == null) {
            return;
        }
        bool.filter(f -> f.range(r -> {
            r.field("occurredAt");
            if (from != null) {
                r.gte(co.elastic.clients.json.JsonData.of(from.toString()));
            }
            if (to != null) {
                r.lte(co.elastic.clients.json.JsonData.of(to.toString()));
            }
            return r;
        }));
    }

    private static void addTermIfPresent(BoolQuery.Builder bool, String field, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        bool.filter(f -> f.term(t -> t.field(field).value(value.trim())));
    }

    private static String escapeWildcard(String raw) {
        return raw.replace("\\", "\\\\")
                .replace("*", "\\*")
                .replace("?", "\\?");
    }

    private static boolean isIndexMissing(Throwable ex) {
        Throwable cur = ex;
        while (cur != null) {
            String name = cur.getClass().getName();
            if (name.contains("NoSuchIndexException") || name.contains("IndexNotFoundException")) {
                return true;
            }
            String msg = cur.getMessage();
            if (msg != null && (msg.contains("index_not_found")
                    || msg.contains("no such index")
                    || msg.contains("Index") && msg.contains("not found"))) {
                return true;
            }
            cur = cur.getCause();
        }
        return false;
    }

    private static RuntimeException translateEs(Exception ex) {
        if (isEsUnavailable(ex)) {
            return BizException.serviceUnavailable(
                    "审计存储不可用：无法连接 Elasticsearch（默认 http://127.0.0.1:9200）。请先启动 ES 后重试");
        }
        if (isMappingConflict(ex)) {
            return BizException.badRequest(
                    "审计索引映射冲突，请删除旧索引后重启 dbc-audit 以应用最新模板（details 为 enabled=false）");
        }
        if (ex instanceof RuntimeException runtime) {
            return runtime;
        }
        return new RuntimeException(ex);
    }

    private static boolean isMappingConflict(Throwable ex) {
        Throwable cur = ex;
        while (cur != null) {
            String msg = cur.getMessage() == null ? "" : cur.getMessage();
            if (msg.contains("can't merge")
                    || msg.contains("mapper_parsing_exception")
                    || msg.contains("illegal_argument_exception")) {
                return true;
            }
            cur = cur.getCause();
        }
        return false;
    }

    private static boolean isEsUnavailable(Throwable ex) {
        Throwable cur = ex;
        while (cur != null) {
            String name = cur.getClass().getName();
            String msg = cur.getMessage() == null ? "" : cur.getMessage();
            if (name.contains("DataAccessResourceFailure")
                    || name.contains("ConnectionClosed")
                    || name.contains("ConnectException")
                    || name.contains("SocketException")
                    || msg.contains("Connection is closed")
                    || msg.contains("Connection refused")
                    || msg.contains("Connection reset")
                    || msg.contains("Failed to connect")) {
                return true;
            }
            cur = cur.getCause();
        }
        return false;
    }
}
