package com.lyj.dbc.audit.es;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

import java.util.Map;

/**
 * 审计 ES 文档。
 * <p>
 * {@code occurredAt} 存 ISO-8601<strong>毫秒</strong>字符串（与索引模板 date 一致）。
 * 不用 {@link Instant} 作属性类型：Spring Data ES 的 Temporal 转换器无法解析纳秒精度（如 {@code .502655700Z}），
 * 会导致列表/详情 ConversionException。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditDocument {

    @Id
    @Field(type = FieldType.Keyword)
    private String eventId;

    @Field(type = FieldType.Keyword)
    private String category;

    /** ISO-8601 毫秒，如 2026-09-15T02:21:28.502Z；读写均按字符串，避免 Instant 转换失败 */
    @Field(type = FieldType.Keyword)
    private String occurredAt;

    @Field(type = FieldType.Long)
    private Long operatorUserId;

    @Field(type = FieldType.Keyword)
    private String operatorUsername;

    @Field(type = FieldType.Keyword)
    private String clientIp;

    @Field(type = FieldType.Keyword)
    private String traceId;

    @Field(type = FieldType.Keyword)
    private String module;

    @Field(type = FieldType.Keyword)
    private String action;

    @Field(type = FieldType.Keyword)
    private String resourceType;

    @Field(type = FieldType.Keyword)
    private String resourceId;

    @Field(type = FieldType.Keyword)
    private String result;

    @Field(type = FieldType.Text)
    private String failReason;

    /** 自由结构：只存 _source，不建嵌套 mapping（见 AuditIndexMappings） */
    @Field(type = FieldType.Object, enabled = false)
    private Map<String, Object> details;

    @Field(type = FieldType.Keyword)
    private String batchId;

    @Field(type = FieldType.Integer)
    private Integer statementIndex;

    @Field(type = FieldType.Long)
    private Long workspaceId;

    @Field(type = FieldType.Keyword)
    private String workspaceName;

    @Field(type = FieldType.Long)
    private Long connectionId;

    @Field(type = FieldType.Keyword)
    private String connectionName;

    @Field(type = FieldType.Keyword)
    private String dbType;

    @Field(type = FieldType.Keyword)
    private String status;

    @Field(type = FieldType.Keyword)
    private String statementType;

    @Field(type = FieldType.Text)
    private String sqlText;

    @Field(type = FieldType.Boolean)
    private Boolean sqlTruncated;

    @Field(type = FieldType.Long)
    private Long elapsedMs;

    /** 自由结构：只存 _source，不建嵌套 mapping */
    @Field(type = FieldType.Object, enabled = false)
    private Map<String, Object> failDetail;
}
