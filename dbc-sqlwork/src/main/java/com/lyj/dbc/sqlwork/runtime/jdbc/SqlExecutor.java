package com.lyj.dbc.sqlwork.runtime.jdbc;

import com.lyj.dbc.sqlwork.api.vo.ExecuteResult;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 单语句 JDBC 执行：SELECT 截断行数，DML 返回影响行数。
 * <p>
 * 支持池借还与外部租约连接（事务会话）两种模式。
 */
@Component
public class SqlExecutor {

    private static final Logger log = LoggerFactory.getLogger(SqlExecutor.class);

    private final SqlworkProperties properties;

    public SqlExecutor(SqlworkProperties properties) {
        this.properties = properties;
    }

    /** 从池借连接执行后归还（自动提交路径）。 */
    public ExecuteResult.StatementResult execute(DataSource dataSource, String sql, String statementType,
                                                   int maxRows, String schema) {
        long start = System.currentTimeMillis();
        int timeout = Math.max(1, properties.getExecuteTimeoutSeconds());
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            stmt.setQueryTimeout(timeout);
            applySchema(conn, schema);
            return runOnStatement(stmt, sql, statementType, maxRows, start);
        } catch (SQLException ex) {
            log.warn("SQL 执行失败", ex);
            throw BizException.badRequest("SQL 执行失败: " + ex.getMessage());
        }
    }

    /**
     * 在已有连接上执行（事务租约）；不关闭连接。
     *
     * @param applySchemaOnce 是否设置 search_path（租约内首次建议 true）
     */
    public ExecuteResult.StatementResult executeOnConnection(Connection conn, String sql, String statementType,
                                                             int maxRows, String schema, boolean applySchemaOnce) {
        long start = System.currentTimeMillis();
        int timeout = Math.max(1, properties.getExecuteTimeoutSeconds());
        try (Statement stmt = conn.createStatement()) {
            stmt.setQueryTimeout(timeout);
            if (applySchemaOnce) {
                applySchema(conn, schema);
            }
            return runOnStatement(stmt, sql, statementType, maxRows, start);
        } catch (SQLException ex) {
            log.warn("SQL 执行失败（租约连接）", ex);
            throw BizException.badRequest("SQL 执行失败: " + ex.getMessage());
        }
    }

    /** 从池借出连接并关闭 autoCommit，供 BEGIN 租约使用（调用方负责关闭）。 */
    public Connection borrowForTransaction(DataSource dataSource, String schema) {
        try {
            Connection conn = dataSource.getConnection();
            conn.setAutoCommit(false);
            applySchema(conn, schema);
            return conn;
        } catch (SQLException ex) {
            log.warn("借出事务连接失败", ex);
            throw BizException.badRequest("开启事务失败: " + ex.getMessage());
        }
    }

    private ExecuteResult.StatementResult runOnStatement(Statement stmt, String sql, String statementType,
                                                         int maxRows, long start) throws SQLException {
        boolean hasResultSet = stmt.execute(sql);
        long elapsed = System.currentTimeMillis() - start;
        if (hasResultSet) {
            try (ResultSet rs = stmt.getResultSet()) {
                return readResultSet(rs, statementType, maxRows, elapsed);
            }
        }
        int affected = stmt.getUpdateCount();
        return ExecuteResult.StatementResult.builder()
                .columns(Collections.emptyList())
                .rows(Collections.emptyList())
                .rowCount(0)
                .truncated(false)
                .elapsedMs(elapsed)
                .statementType(statementType)
                .affectedRows(Math.max(affected, 0))
                .success(true)
                .message("ok")
                .build();
    }

    private void applySchema(Connection conn, String schema) throws SQLException {
        if (schema == null || schema.isBlank()) {
            return;
        }
        String trimmed = schema.trim();
        if (!trimmed.matches("[A-Za-z0-9_]+")) {
            throw BizException.badRequest("非法 schema 名称");
        }
        try (Statement setStmt = conn.createStatement()) {
            setStmt.execute("SET search_path TO " + trimmed);
        } catch (SQLException ex) {
            log.debug("设置 search_path 失败（可能非 PG）: {}", ex.getMessage());
        }
    }

    private ExecuteResult.StatementResult readResultSet(ResultSet rs, String statementType, int maxRows, long elapsed)
            throws SQLException {
        ResultSetMetaData meta = rs.getMetaData();
        int colCount = meta.getColumnCount();
        List<ExecuteResult.ColumnMeta> columns = new ArrayList<>(colCount);
        for (int i = 1; i <= colCount; i++) {
            columns.add(new ExecuteResult.ColumnMeta(meta.getColumnLabel(i), meta.getColumnTypeName(i)));
        }
        List<List<Object>> rows = new ArrayList<>();
        boolean truncated = false;
        while (rs.next()) {
            if (rows.size() >= maxRows) {
                truncated = true;
                break;
            }
            List<Object> row = new ArrayList<>(colCount);
            for (int i = 1; i <= colCount; i++) {
                row.add(rs.getObject(i));
            }
            rows.add(row);
        }
        return ExecuteResult.StatementResult.builder()
                .columns(columns)
                .rows(rows)
                .rowCount(rows.size())
                .truncated(truncated)
                .elapsedMs(elapsed)
                .statementType(statementType)
                .affectedRows(null)
                .success(true)
                .message(truncated ? "结果已截断至 " + maxRows + " 行" : "ok")
                .build();
    }
}
