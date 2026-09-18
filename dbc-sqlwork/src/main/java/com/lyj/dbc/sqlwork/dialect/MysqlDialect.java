package com.lyj.dbc.sqlwork.dialect;

import com.lyj.dbc.sqlwork.common.BizException;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.util.List;

/**
 * MySQL 方言占位：接口齐全，执行/元数据方法尚未启用。
 */
@Component
public class MysqlDialect implements DbDialect {

    private static final String MSG = "MySQL 方言尚未启用";

    @Override
    public DbType dbType() {
        return DbType.MYSQL;
    }

    @Override
    public String probeSql() {
        throw BizException.badRequest(MSG);
    }

    @Override
    public String buildJdbcUrl(String host, int port, String database) {
        throw BizException.badRequest(MSG);
    }

    @Override
    public List<String> listDatabases(Connection connection) {
        throw BizException.badRequest(MSG);
    }

    @Override
    public List<String> listSchemas(Connection connection, String database) {
        throw BizException.badRequest(MSG);
    }

    @Override
    public TablePage listTables(Connection connection, String database, String schema,
                                String keyword, java.util.Collection<String> nameAllowlist,
                                int page, int size) {
        throw BizException.badRequest(MSG);
    }
}
