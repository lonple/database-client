package com.lyj.dbc.audit.es;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.indices.PutIndexTemplateRequest;
import com.lyj.dbc.audit.config.AuditProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 启动时创建/更新审计索引模板（幂等 put）。映射见 {@link AuditIndexMappings}。
 */
@Component
@Order(5)
public class AuditIndexTemplateBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AuditIndexTemplateBootstrap.class);

    /** 模板版本后缀：映射不兼容时递增，避免与旧模板 silently 混用 */
    static final int TEMPLATE_VERSION = 2;

    private final ElasticsearchClient elasticsearchClient;
    private final AuditIndexNames indexNames;
    private final AuditProperties properties;

    public AuditIndexTemplateBootstrap(ElasticsearchClient elasticsearchClient,
                                       AuditIndexNames indexNames,
                                       AuditProperties properties) {
        this.elasticsearchClient = elasticsearchClient;
        this.indexNames = indexNames;
        this.properties = properties;
    }

    @Override
    public void run(ApplicationArguments args) {
        try {
            putTemplate(templateName("biz"), List.of(indexNames.bizSearchPattern()));
            putTemplate(templateName("sql"), List.of(indexNames.sqlSearchPattern()));
            log.info("审计 ES 索引模板已就绪 v{} patterns=[{}, {}]",
                    TEMPLATE_VERSION, indexNames.bizSearchPattern(), indexNames.sqlSearchPattern());
        } catch (Exception e) {
            log.warn("审计 ES 索引模板注册失败（查询/写入可能异常）: {}", e.getMessage(), e);
        }
    }

    String templateName(String kind) {
        return safeEnv() + "-dbc-audit-" + kind + "-template-v" + TEMPLATE_VERSION;
    }

    private String safeEnv() {
        String env = properties.getIndexEnv();
        return env == null || env.isBlank() ? "dev" : env.trim();
    }

    private void putTemplate(String name, List<String> patterns) throws Exception {
        PutIndexTemplateRequest request = PutIndexTemplateRequest.of(r -> r
                .name(name)
                .indexPatterns(patterns)
                .priority(300)
                .template(t -> t
                        .settings(s -> s
                                .numberOfShards("1")
                                .numberOfReplicas("0")
                        )
                        .mappings(AuditIndexMappings.typeMapping())
                )
        );
        elasticsearchClient.indices().putIndexTemplate(request);
        log.info("已 put 索引模板 name={} patterns={}", name, patterns);
    }
}
