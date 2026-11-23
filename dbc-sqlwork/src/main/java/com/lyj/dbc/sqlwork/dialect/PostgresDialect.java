package com.lyj.dbc.sqlwork.dialect;

import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * PostgreSQL 方言实现。
 */
@Component
public class PostgresDialect implements DbDialect {

    @Override
    public DbType dbType() {
        return DbType.POSTGRESQL;
    }

    @Override
    public String probeSql() {
        return "SELECT 1";
    }

    @Override
    public String buildJdbcUrl(String host, int port, String database) {
        String db = (database == null || database.isBlank()) ? "postgres" : database;
        return "jdbc:postgresql://" + host + ":" + port + "/" + db;
    }

    @Override
    public List<String> listDatabases(Connection connection) throws SQLException {
        String sql = "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname";
        List<String> result = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                result.add(rs.getString(1));
            }
        }
        return result;
    }

    @Override
    public List<String> listSchemas(Connection connection, String database) throws SQLException {
        String sql = """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE catalog_name = COALESCE(?, current_database())
                ORDER BY schema_name
                """;
        List<String> result = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            if (database == null || database.isBlank()) {
                ps.setNull(1, java.sql.Types.VARCHAR);
            } else {
                ps.setString(1, database);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    result.add(rs.getString(1));
                }
            }
        }
        return result;
    }

    @Override
    public TablePage listTables(Connection connection, String database, String schema,
                                String keyword, java.util.Collection<String> nameAllowlist,
                                int page, int size) throws SQLException {
        int safePage = Math.max(page, 1);
        int safeSize = Math.max(size, 1);
        int offset = (safePage - 1) * safeSize;

        List<String> names = normalizeAllowlist(nameAllowlist);
        if (names != null && names.isEmpty()) {
            return new TablePage(List.of(), 0);
        }

        StringBuilder filters = new StringBuilder("""
                WHERE t.table_catalog = COALESCE(?, current_database())
                """);
        List<Object> params = new ArrayList<>();
        params.add(blankToNull(database));

        if (schema != null && !schema.isBlank()) {
            filters.append(" AND t.table_schema = ?");
            params.add(schema);
        } else {
            filters.append(" AND t.table_schema NOT IN ('pg_catalog', 'information_schema')");
        }
        if (keyword != null && !keyword.isBlank()) {
            filters.append(" AND t.table_name ILIKE ?");
            params.add("%" + keyword.trim() + "%");
        }
        if (names != null) {
            filters.append(" AND t.table_name IN (");
            for (int i = 0; i < names.size(); i++) {
                if (i > 0) {
                    filters.append(',');
                }
                filters.append('?');
                params.add(names.get(i));
            }
            filters.append(')');
        }

        long total;
        String countSql = "SELECT COUNT(*) FROM information_schema.tables t " + filters;
        try (PreparedStatement ps = connection.prepareStatement(countSql)) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                total = rs.getLong(1);
            }
        }

        String dataSql = """
                SELECT t.table_schema, t.table_name,
                       CASE WHEN t.table_type = 'VIEW' THEN 'VIEW' ELSE 'TABLE' END AS object_type,
                       d.description AS table_comment
                FROM information_schema.tables t
                LEFT JOIN pg_catalog.pg_namespace n ON n.nspname = t.table_schema
                LEFT JOIN pg_catalog.pg_class cls
                       ON cls.relnamespace = n.oid AND cls.relname = t.table_name
                      AND cls.relkind IN ('r', 'p', 'v', 'm', 'f')
                LEFT JOIN pg_catalog.pg_description d
                       ON d.objoid = cls.oid AND d.objsubid = 0
                """ + filters + " ORDER BY t.table_schema, t.table_name LIMIT ? OFFSET ?";
        List<Object> dataParams = new ArrayList<>(params);
        dataParams.add(safeSize);
        dataParams.add(offset);

        List<TableItem> items = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(dataSql)) {
            bind(ps, dataParams);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    items.add(new TableItem(
                            rs.getString(1), rs.getString(2), rs.getString(3), rs.getString(4)));
                }
            }
        }
        return new TablePage(items, total);
    }

    @Override
    public List<ColumnItem> listColumns(Connection connection, String database, String schema, String table)
            throws SQLException {
        if (table == null || table.isBlank()) {
            throw new SQLException("table 不能为空");
        }
        String sql = """
                SELECT c.column_name, c.data_type,
                       (c.is_nullable = 'YES') AS nullable,
                       d.description AS comment,
                       c.ordinal_position
                FROM information_schema.columns c
                LEFT JOIN pg_catalog.pg_namespace n ON n.nspname = c.table_schema
                LEFT JOIN pg_catalog.pg_class cls
                       ON cls.relnamespace = n.oid AND cls.relname = c.table_name
                      AND cls.relkind IN ('r', 'p', 'v', 'm', 'f')
                LEFT JOIN pg_catalog.pg_description d
                       ON d.objoid = cls.oid AND d.objsubid = c.ordinal_position
                WHERE c.table_catalog = COALESCE(?, current_database())
                  AND c.table_schema = COALESCE(?, current_schema())
                  AND c.table_name = ?
                ORDER BY c.ordinal_position
                """;
        List<ColumnItem> items = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(sql)) {
            ps.setString(1, blankToNull(database));
            ps.setString(2, blankToNull(schema));
            ps.setString(3, table.trim());
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    items.add(new ColumnItem(
                            rs.getString(1),
                            rs.getString(2),
                            rs.getBoolean(3),
                            rs.getString(4),
                            rs.getInt(5)));
                }
            }
        }
        return items;
    }

    private static List<String> normalizeAllowlist(java.util.Collection<String> nameAllowlist) {
        if (nameAllowlist == null) {
            return null;
        }
        List<String> names = new ArrayList<>();
        for (String n : nameAllowlist) {
            if (n != null && !n.isBlank()) {
                names.add(n.trim());
            }
        }
        return names;
    }

    private static String blankToNull(String value) {
        return (value == null || value.isBlank()) ? null : value;
    }

    private static void bind(PreparedStatement ps, List<Object> params) throws SQLException {
        for (int i = 0; i < params.size(); i++) {
            Object v = params.get(i);
            if (v == null) {
                ps.setNull(i + 1, java.sql.Types.VARCHAR);
            } else if (v instanceof Integer iv) {
                ps.setInt(i + 1, iv);
            } else {
                ps.setObject(i + 1, v);
            }
        }
    }
}
