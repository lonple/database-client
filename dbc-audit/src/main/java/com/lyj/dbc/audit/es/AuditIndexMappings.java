package com.lyj.dbc.audit.es;

import co.elastic.clients.elasticsearch._types.mapping.DynamicMapping;
import co.elastic.clients.elasticsearch._types.mapping.Property;
import co.elastic.clients.elasticsearch._types.mapping.TypeMapping;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 审计索引映射定案（与 {@link AuditIndexTemplateBootstrap} 共用，便于单测断言）。
 *
 * <h3>兼容性原则</h3>
 * <ul>
 *   <li>顶层字段显式声明，{@code dynamic=false}，禁止业务随意涨字段污染映射。</li>
 *   <li>{@code occurredAt} 固定 date（strict_date_optional_time || epoch_millis），禁止动态成 long。</li>
 *   <li>{@code details}/{@code failDetail}：{@code enabled=false}，只进 _source、不建嵌套 mapping。
 *       UPDATE 的 {@code changes[].before/after} 可能是标量也可能是对象，若开启动态映射会
 *       illegal_argument_exception（can't merge non object with object）。</li>
 *   <li>检索依赖顶层 keyword/text；详情抽屉读 _source JSON，不依赖 details 内字段可搜。</li>
 * </ul>
 */
public final class AuditIndexMappings {

    private AuditIndexMappings() {
    }

    public static TypeMapping typeMapping() {
        return TypeMapping.of(m -> m
                .dynamic(DynamicMapping.False)
                .properties(properties()));
    }

    public static Map<String, Property> properties() {
        Map<String, Property> props = new LinkedHashMap<>();
        props.put("eventId", keyword());
        props.put("category", keyword());
        // 毫秒 ISO 与 epoch_millis 均可；禁止无模板时动态成 long 再被当成 Instant 炸转换
        props.put("occurredAt", Property.of(p -> p.date(d -> d
                .format("strict_date_optional_time||epoch_millis"))));
        props.put("operatorUserId", Property.of(p -> p.long_(l -> l)));
        props.put("operatorUsername", keyword());
        props.put("clientIp", keyword());
        props.put("traceId", keyword());

        props.put("module", keyword());
        props.put("action", keyword());
        props.put("resourceType", keyword());
        props.put("resourceId", keyword());
        props.put("result", keyword());
        props.put("failReason", Property.of(p -> p.text(t -> t)));
        // 关键：自由结构只存 _source
        props.put("details", opaqueObject());
        props.put("failDetail", opaqueObject());

        props.put("batchId", keyword());
        props.put("statementIndex", Property.of(p -> p.integer(i -> i)));
        props.put("workspaceId", Property.of(p -> p.long_(l -> l)));
        props.put("workspaceName", keyword());
        props.put("connectionId", Property.of(p -> p.long_(l -> l)));
        props.put("connectionName", keyword());
        props.put("dbType", keyword());
        props.put("status", keyword());
        props.put("statementType", keyword());
        props.put("sqlText", Property.of(p -> p.text(t -> t)));
        props.put("sqlTruncated", Property.of(p -> p.boolean_(b -> b)));
        props.put("elapsedMs", Property.of(p -> p.long_(l -> l)));
        return props;
    }

    /** 只存 _source，不建立子字段 mapping，避免嵌套类型冲突。 */
    static Property opaqueObject() {
        return Property.of(p -> p.object(o -> o.enabled(false)));
    }

    static Property keyword() {
        return Property.of(p -> p.keyword(k -> k.ignoreAbove(1024)));
    }
}
