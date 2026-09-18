package com.lyj.dbc.audit.es;

import co.elastic.clients.elasticsearch._types.mapping.Property;
import co.elastic.clients.elasticsearch._types.mapping.TypeMapping;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 索引映射契约：details/failDetail 必须 enabled=false，避免嵌套类型冲突。
 */
class AuditIndexMappingsTest {

    @Test
    void detailsAndFailDetail_areOpaqueObjects() {
        Map<String, Property> props = AuditIndexMappings.properties();
        assertThat(props.get("details").isObject()).isTrue();
        assertThat(props.get("details").object().enabled()).isFalse();
        assertThat(props.get("failDetail").isObject()).isTrue();
        assertThat(props.get("failDetail").object().enabled()).isFalse();
    }

    @Test
    void occurredAt_isDateWithCompatibleFormats() {
        Property occurredAt = AuditIndexMappings.properties().get("occurredAt");
        assertThat(occurredAt.isDate()).isTrue();
        assertThat(occurredAt.date().format()).contains("strict_date_optional_time");
        assertThat(occurredAt.date().format()).contains("epoch_millis");
    }

    @Test
    void typeMapping_dynamicFalse() {
        TypeMapping mapping = AuditIndexMappings.typeMapping();
        assertThat(mapping.dynamic()).isNotNull();
        assertThat(mapping.dynamic().jsonValue()).isEqualTo("false");
    }

    @Test
    void topLevelSearchFields_arePresent() {
        Map<String, Property> props = AuditIndexMappings.properties();
        assertThat(props.keySet()).contains(
                "eventId", "category", "occurredAt", "module", "action",
                "operatorUsername", "result", "sqlText", "status");
    }
}
