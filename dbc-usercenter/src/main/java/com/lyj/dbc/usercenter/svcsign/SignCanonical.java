package com.lyj.dbc.usercenter.svcsign;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/**
 * 构造服务间请求待签字符串。
 */
public final class SignCanonical {

    private SignCanonical() {
    }

    public static String build(String method, String path, String queryString,
                               String timestamp, String nonce, byte[] body) {
        String m = method == null ? "" : method.trim().toUpperCase(Locale.ROOT);
        String p = path == null || path.isEmpty() ? "/" : path;
        String q = canonicalQuery(queryString);
        String bodyHash = sha256Hex(body == null ? new byte[0] : body);
        return m + "\n" + p + "\n" + q + "\n" + timestamp + "\n" + nonce + "\n" + bodyHash;
    }

    public static String canonicalQuery(String queryString) {
        if (queryString == null || queryString.isBlank()) {
            return "";
        }
        String raw = queryString.startsWith("?") ? queryString.substring(1) : queryString;
        Map<String, List<String>> map = new TreeMap<>();
        for (String part : raw.split("&")) {
            if (part.isEmpty()) {
                continue;
            }
            int idx = part.indexOf('=');
            String k = idx >= 0 ? part.substring(0, idx) : part;
            String v = idx >= 0 ? part.substring(idx + 1) : "";
            map.computeIfAbsent(k, key -> new ArrayList<>()).add(v);
        }
        List<String> pairs = new ArrayList<>();
        for (Map.Entry<String, List<String>> e : map.entrySet()) {
            List<String> values = e.getValue();
            Collections.sort(values);
            for (String v : values) {
                pairs.add(e.getKey() + "=" + v);
            }
        }
        return String.join("&", pairs);
    }

    public static String sha256Hex(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            StringBuilder sb = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new IllegalStateException("SHA-256 失败", e);
        }
    }

    public static byte[] utf8(String s) {
        return s == null ? new byte[0] : s.getBytes(StandardCharsets.UTF_8);
    }
}
