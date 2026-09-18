package com.lyj.dbc.manage.asset;

/**
 * 支持的数据库类型。
 */
public enum DbType {
    POSTGRESQL,
    MYSQL,
    ORACLE,
    SQLSERVER,
    MARIADB;

    public String defaultDriverClassName() {
        return switch (this) {
            case POSTGRESQL -> "org.postgresql.Driver";
            case MYSQL, MARIADB -> "com.mysql.cj.jdbc.Driver";
            case ORACLE -> "oracle.jdbc.OracleDriver";
            case SQLSERVER -> "com.microsoft.sqlserver.jdbc.SQLServerDriver";
        };
    }

    public static DbType from(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("dbType 不能为空");
        }
        return DbType.valueOf(value.trim().toUpperCase());
    }
}
