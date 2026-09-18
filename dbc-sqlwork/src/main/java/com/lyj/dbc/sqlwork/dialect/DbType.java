package com.lyj.dbc.sqlwork.dialect;

/**
 * 支持的数据库类型（与 manage asset 枚举对齐）。
 */
public enum DbType {
    POSTGRESQL,
    MYSQL;

    public String defaultDriverClassName() {
        return switch (this) {
            case POSTGRESQL -> "org.postgresql.Driver";
            case MYSQL -> "com.mysql.cj.jdbc.Driver";
        };
    }

    public static DbType from(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("dbType 不能为空");
        }
        return DbType.valueOf(value.trim().toUpperCase());
    }
}
