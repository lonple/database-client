package com.lyj.dbc.sqlwork.dialect;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;

/**
 * 目标库方言 SPI：探活、JDBC URL、元数据查询等差异均收敛于此。
 */
public interface DbDialect {

    /** 方言对应的库类型 */
    DbType dbType();

    /** 连接探活 SQL */
    String probeSql();

    /** 组装 JDBC URL */
    String buildJdbcUrl(String host, int port, String database);

    /** 默认驱动类名 */
    default String defaultDriverClassName() {
        return dbType().defaultDriverClassName();
    }

    /** 列出数据库（catalog） */
    List<String> listDatabases(Connection connection) throws SQLException;

    /** 列出 schema；database 可为当前库 */
    List<String> listSchemas(Connection connection, String database) throws SQLException;

    /**
     * 分页列出表/视图。
     *
     * @param keyword       表名模糊匹配，可空
     * @param nameAllowlist 非空时仅查这些表名（IN 下推）；空/null 表示不限制表名
     * @param page          从 1 开始
     * @param size          页大小
     */
    TablePage listTables(Connection connection, String database, String schema,
                         String keyword, java.util.Collection<String> nameAllowlist,
                         int page, int size) throws SQLException;

    /**
     * 兼容旧调用：无表名白名单。
     */
    default TablePage listTables(Connection connection, String database, String schema,
                                 String keyword, int page, int size) throws SQLException {
        return listTables(connection, database, schema, keyword, null, page, size);
    }

    /**
     * 表分页结果。
     */
    record TablePage(List<TableItem> items, long total) {
    }

    /**
     * 表/视图项。
     */
    record TableItem(String schema, String name, String objectType) {
    }
}
