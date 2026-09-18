package com.lyj.dbc.client.audit;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 审计 details 归一化：保证 UPDATE changes 的 before/after 可稳定序列化展示。
 * <p>
 * ES 侧 {@code details} 已 {@code enabled=false}，不依赖本类防 mapping 冲突；
 * 本类仍将复杂对象转为 JSON 字符串，避免前端/下游对「同一字段有时是对象有时是标量」处理分裂。
 */
public final class AuditDetailsNormalizer {

    private AuditDetailsNormalizer() {
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> normalize(Map<String, Object> details, ObjectMapper objectMapper) {
        if (details == null || details.isEmpty()) {
            return details;
        }
        Object changes = details.get("changes");
        if (!(changes instanceof List<?> list) || list.isEmpty()) {
            return details;
        }
        List<Object> normalized = new ArrayList<>(list.size());
        for (Object row : list) {
            if (!(row instanceof Map<?, ?> map)) {
                normalized.add(row);
                continue;
            }
            Map<String, Object> copy = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : map.entrySet()) {
                String key = String.valueOf(e.getKey());
                Object val = e.getValue();
                if ("before".equals(key) || "after".equals(key)) {
                    copy.put(key, toDisplayValue(val, objectMapper));
                } else {
                    copy.put(key, val);
                }
            }
            normalized.add(copy);
        }
        Map<String, Object> out = new LinkedHashMap<>(details);
        out.put("changes", normalized);
        return out;
    }

    static Object toDisplayValue(Object value, ObjectMapper objectMapper) {
        if (value == null) {
            return null;
        }
        if (value instanceof String || value instanceof Number || value instanceof Boolean) {
            return value;
        }
        if (value instanceof Map<?, ?> || value instanceof Collection<?> || value.getClass().isArray()) {
            try {
                return objectMapper.writeValueAsString(value);
            } catch (Exception e) {
                return String.valueOf(value);
            }
        }
        return String.valueOf(value);
    }
}
