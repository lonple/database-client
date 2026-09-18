package com.lyj.dbc.manage.authz;

import java.util.Locale;
import java.util.Set;

/**
 * 授权对象范围编码。
 */
public final class ObjectScopeCodes {

    /** 整个连接（兼容旧值 ALL_TABLES） */
    public static final String CONNECTION = "CONNECTION";
    /** 兼容旧值 */
    public static final String ALL_TABLES = "ALL_TABLES";
    /** 若干库（库下全部模式/表） */
    public static final String DATABASE = "DATABASE";
    /** 若干模式（模式下全部表） */
    public static final String SCHEMA = "SCHEMA";
    /** 若干表（兼容旧值 SPECIFIC_TABLES） */
    public static final String TABLE = "TABLE";
    /** 兼容旧值 */
    public static final String SPECIFIC_TABLES = "SPECIFIC_TABLES";

    private static final Set<String> WHOLE_CONNECTION = Set.of(CONNECTION, ALL_TABLES);
    private static final Set<String> TABLE_LEVEL = Set.of(TABLE, SPECIFIC_TABLES);

    private ObjectScopeCodes() {
    }

    public static String normalize(String raw) {
        if (raw == null || raw.isBlank()) {
            return CONNECTION;
        }
        String s = raw.trim().toUpperCase(Locale.ROOT);
        if (ALL_TABLES.equals(s)) {
            return CONNECTION;
        }
        if (SPECIFIC_TABLES.equals(s)) {
            return TABLE;
        }
        return s;
    }

    public static boolean isWholeConnection(String scope) {
        return WHOLE_CONNECTION.contains(normalize(scope));
    }

    public static boolean isDatabase(String scope) {
        return DATABASE.equals(normalize(scope));
    }

    public static boolean isSchema(String scope) {
        return SCHEMA.equals(normalize(scope));
    }

    public static boolean isTableLevel(String scope) {
        return TABLE_LEVEL.contains(normalize(scope));
    }

    public static boolean isValid(String scope) {
        String n = normalize(scope);
        return CONNECTION.equals(n) || DATABASE.equals(n) || SCHEMA.equals(n) || TABLE.equals(n);
    }
}
