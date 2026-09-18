package com.lyj.dbc.client.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AuditDetailsNormalizerTest {

    private final ObjectMapper om = new ObjectMapper();

    @Test
    void normalize_mixedScalarAndObject_beforeAfterBecomeStable() {
        Map<String, Object> row1 = new LinkedHashMap<>();
        row1.put("field", "username");
        row1.put("before", "a");
        row1.put("after", "b");

        Map<String, Object> row2 = new LinkedHashMap<>();
        row2.put("field", "profile");
        row2.put("before", Map.of("title", "dev"));
        row2.put("after", Map.of("title", "lead", "level", 2));

        Map<String, Object> details = Map.of("changes", List.of(row1, row2));
        Map<String, Object> out = AuditDetailsNormalizer.normalize(details, om);

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> changes = (List<Map<String, Object>>) out.get("changes");
        assertThat(changes.get(0).get("before")).isEqualTo("a");
        assertThat(changes.get(0).get("after")).isEqualTo("b");
        assertThat(changes.get(1).get("before")).isInstanceOf(String.class);
        assertThat((String) changes.get(1).get("before")).contains("dev");
        assertThat(changes.get(1).get("after")).isInstanceOf(String.class);
        assertThat((String) changes.get(1).get("after")).contains("lead");
    }

    @Test
    void normalize_nullOrEmpty_passthrough() {
        assertThat(AuditDetailsNormalizer.normalize(null, om)).isNull();
        assertThat(AuditDetailsNormalizer.normalize(Map.of(), om)).isEmpty();
        assertThat(AuditDetailsNormalizer.normalize(Map.of("username", "x"), om))
                .containsEntry("username", "x");
    }
}
