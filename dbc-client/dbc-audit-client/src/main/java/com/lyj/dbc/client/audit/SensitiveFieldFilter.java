package com.lyj.dbc.client.audit;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 敏感字段禁入：序列化前从 Map 树中剔除，不做「记了再脱敏」。
 */
public final class SensitiveFieldFilter {

    private static final Pattern NAME = Pattern.compile(
            ".*(password|passwd|pwd|secret|cipher|token|credential|private.?key|reauth).*",
            Pattern.CASE_INSENSITIVE);

    private SensitiveFieldFilter() {
    }

    public static boolean isSensitiveName(String name) {
        if (name == null || name.isBlank()) {
            return false;
        }
        String n = name.trim();
        String lower = n.toLowerCase(Locale.ROOT);
        if ("password".equals(lower) || "passwd".equals(lower) || "pwd".equals(lower)
                || "token".equals(lower) || "secret".equals(lower)
                || "secretcipher".equals(lower) || "refreshtoken".equals(lower)
                || "reauthticket".equals(lower) || "authorization".equals(lower)) {
            return true;
        }
        return NAME.matcher(n).matches();
    }

    @SuppressWarnings("unchecked")
    public static Object sanitize(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> out = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : map.entrySet()) {
                String key = e.getKey() == null ? null : String.valueOf(e.getKey());
                if (isSensitiveName(key)) {
                    continue;
                }
                out.put(key, sanitize(e.getValue()));
            }
            return out;
        }
        if (value instanceof List<?> list) {
            List<Object> out = new ArrayList<>(list.size());
            for (Object item : list) {
                out.add(sanitize(item));
            }
            return out;
        }
        return value;
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> sanitizeMap(Map<String, Object> details) {
        if (details == null) {
            return null;
        }
        return (Map<String, Object>) sanitize(details);
    }
}
