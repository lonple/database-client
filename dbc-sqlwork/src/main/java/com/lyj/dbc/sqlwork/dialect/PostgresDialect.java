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

        StringBuilder where = new StringBuilder("""
                FROM information_schema.tables
                WHERE table_catalog = COALESCE(?, current_database())
                """);
        List<Object> params = new ArrayList<>();
        params.add(blankToNull(database));

        if (schema != null && !schema.isBlank()) {
            where.append(" AND table_schema = ?");
            params.add(schema);
        } else {
            where.append(" AND table_schema NOT IN ('pg_catalog', 'information_schema')");
        }
        if (keyword != null && !keyword.isBlank()) {
            where.append(" AND table_name ILIKE ?");
            params.add("%" + keyword.trim() + "%");
        }
        if (names != null) {
            where.append(" AND table_name IN (");
            for (int i = 0; i < names.size(); i++) {
                if (i > 0) {
                    where.append(',');
                }
                where.append('?');
                params.add(names.get(i));
            }
            where.append(')');
        }

        long total;
        String countSql = "SELECT COUNT(*) " + where;
        try (PreparedStatement ps = connection.prepareStatement(countSql)) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                total = rs.getLong(1);
            }
        }

        String dataSql = """
                SELECT table_schema, table_name,
                       CASE WHEN table_type = 'VIEW' THEN 'VIEW' ELSE 'TABLE' END AS object_type
                """ + where + " ORDER BY table_schema, table_name LIMIT ? OFFSET ?";
        List<Object> dataParams = new ArrayList<>(params);
        dataParams.add(safeSize);
        dataParams.add(offset);

        List<TableItem> items = new ArrayList<>();
        try (PreparedStatement ps = connection.prepareStatement(dataSql)) {
            bind(ps, dataParams);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    items.add(new TableItem(rs.getString(1), rs.getString(2), rs.getString(3)));
                }
            }
        }
        return new TablePage(items, total);
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
