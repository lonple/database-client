package com.lyj.dbc.sqlwork.pipeline;

import com.alibaba.druid.DbType;
import com.alibaba.druid.sql.SQLUtils;
import com.alibaba.druid.sql.ast.SQLStatement;
import com.alibaba.druid.sql.ast.statement.SQLAlterStatement;
import com.alibaba.druid.sql.ast.statement.SQLCommitStatement;
import com.alibaba.druid.sql.ast.statement.SQLCreateStatement;
import com.alibaba.druid.sql.ast.statement.SQLDeleteStatement;
import com.alibaba.druid.sql.ast.statement.SQLDropStatement;
import com.alibaba.druid.sql.ast.statement.SQLInsertStatement;
import com.alibaba.druid.sql.ast.statement.SQLRollbackStatement;
import com.alibaba.druid.sql.ast.statement.SQLSelectStatement;
import com.alibaba.druid.sql.ast.statement.SQLStartTransactionStatement;
import com.alibaba.druid.sql.ast.statement.SQLTruncateStatement;
import com.alibaba.druid.sql.ast.statement.SQLUpdateStatement;
import com.alibaba.druid.sql.parser.ParserException;
import com.alibaba.druid.sql.visitor.SchemaStatVisitor;
import com.alibaba.druid.stat.TableStat;
import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * SQL 解析（Druid）：按目标库方言拆分多语句，提取语句类型与表引用。
 */
@Service
public class SqlParseService {

    private static final Logger log = LoggerFactory.getLogger(SqlParseService.class);

    private final SqlworkProperties properties;

    public SqlParseService(SqlworkProperties properties) {
        this.properties = properties;
    }

    /**
     * 按方言解析并拆分为语句列表（单批上限可配，默认 50）。
     */
    public List<ParseResult> parseBatch(String sql, String dbType) {
        if (sql == null || sql.isBlank()) {
            throw BizException.badRequest("sql 不能为空");
        }
        String trimmed = sql.trim();
        DbType dialect = resolveDruidDbType(dbType);
        try {
            List<SQLStatement> statements = SQLUtils.parseStatements(trimmed, dialect);
            if (statements == null || statements.isEmpty()) {
                throw BizException.badRequest("无法解析 SQL");
            }
            int maxStatements = Math.max(1, properties.getExecuteMaxStatements());
            if (statements.size() > maxStatements) {
                throw BizException.badRequest("单批最多 " + maxStatements + " 条 SQL 语句");
            }
            List<ParseResult> results = new ArrayList<>(statements.size());
            for (SQLStatement stmt : statements) {
                String text = normalizeSqlText(stmt, dialect);
                if (text.isBlank()) {
                    continue;
                }
                results.add(new ParseResult(
                        refineTxType(resolveType(stmt), text),
                        extractTables(stmt, dialect),
                        text));
            }
            if (results.isEmpty()) {
                throw BizException.badRequest("无法解析 SQL");
            }
            return results;
        } catch (ParserException ex) {
            throw BizException.badRequest("SQL 解析失败: " + ex.getMessage());
        } catch (BizException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("SQL 解析异常 dbType={}", dbType, ex);
            throw BizException.badRequest("SQL 解析失败: " + ex.getMessage());
        }
    }

    static DbType resolveDruidDbType(String dbType) {
        if (dbType == null || dbType.isBlank()) {
            throw BizException.badRequest("连接缺少 dbType，无法按方言解析 SQL");
        }
        String t = dbType.trim().toUpperCase(Locale.ROOT);
        if (t.startsWith("MYSQL") || "MARIADB".equals(t) || "TIDB".equals(t)) {
            return DbType.mysql;
        }
        if ("ORACLE".equals(t)) {
            return DbType.oracle;
        }
        if ("SQLSERVER".equals(t) || "MSSQL".equals(t)) {
            return DbType.sqlserver;
        }
        if ("POSTGRESQL".equals(t) || "POSTGRES".equals(t) || "PG".equals(t)) {
            return DbType.postgresql;
        }
        if ("DM".equals(t) || "DAMENG".equals(t)) {
            return DbType.dm;
        }
        if ("GAUSSDB".equals(t) || "OPENGAUSS".equals(t)) {
            return DbType.gaussdb;
        }
        throw BizException.badRequest("不支持的数据库类型: " + dbType);
    }

    private static String normalizeSqlText(SQLStatement stmt, DbType dialect) {
        String text = SQLUtils.toSQLString(stmt, dialect);
        if (text == null) {
            return "";
        }
        text = text.trim();
        if (text.endsWith(";")) {
            text = text.substring(0, text.length() - 1).trim();
        }
        return text;
    }

    private static String resolveType(SQLStatement stmt) {
        if (stmt instanceof SQLSelectStatement) {
            return "SELECT";
        }
        if (stmt instanceof SQLInsertStatement) {
            return "INSERT";
        }
        if (stmt instanceof SQLUpdateStatement) {
            return "UPDATE";
        }
        if (stmt instanceof SQLDeleteStatement) {
            return "DELETE";
        }
        if (stmt instanceof SQLCreateStatement) {
            return "CREATE";
        }
        if (stmt instanceof SQLAlterStatement) {
            return "ALTER";
        }
        if (stmt instanceof SQLDropStatement) {
            return "DROP";
        }
        if (stmt instanceof SQLTruncateStatement) {
            return "TRUNCATE";
        }
        if (stmt instanceof SQLStartTransactionStatement) {
            return "BEGIN";
        }
        if (stmt instanceof SQLCommitStatement) {
            return "COMMIT";
        }
        if (stmt instanceof SQLRollbackStatement) {
            return "ROLLBACK";
        }
        return "OTHER";
    }

    /**
     * 对解析失败的方言或非标准写法，用文本兜底识别事务控制语句。
     */
    public static String refineTxType(String statementType, String sql) {
        if (statementType != null && !"OTHER".equalsIgnoreCase(statementType)) {
            return statementType;
        }
        if (sql == null || sql.isBlank()) {
            return statementType == null ? "OTHER" : statementType;
        }
        String head = sql.trim().toUpperCase(Locale.ROOT);
        if (head.startsWith("BEGIN") || head.startsWith("START TRANSACTION") || head.startsWith("START WORK")) {
            return "BEGIN";
        }
        if (head.startsWith("COMMIT")) {
            return "COMMIT";
        }
        if (head.startsWith("ROLLBACK")) {
            return "ROLLBACK";
        }
        return statementType == null ? "OTHER" : statementType;
    }

    public static boolean isTxControl(String statementType) {
        if (statementType == null) {
            return false;
        }
        String t = statementType.trim().toUpperCase(Locale.ROOT);
        return "BEGIN".equals(t) || "COMMIT".equals(t) || "ROLLBACK".equals(t);
    }

    private static List<AuthzEvaluateRequest.TableRef> extractTables(SQLStatement stmt, DbType dialect) {
        List<AuthzEvaluateRequest.TableRef> refs = new ArrayList<>();
        try {
            SchemaStatVisitor visitor = SQLUtils.createSchemaStatVisitor(dialect);
            stmt.accept(visitor);
            Map<TableStat.Name, TableStat> tables = visitor.getTables();
            if (tables == null || tables.isEmpty()) {
                return refs;
            }
            Set<String> seen = new LinkedHashSet<>();
            for (TableStat.Name name : tables.keySet()) {
                if (name == null) {
                    continue;
                }
                String raw = name.getName();
                if (raw == null || raw.isBlank()) {
                    continue;
                }
                String cleaned = raw.replace("\"", "").replace("`", "").replace("[", "").replace("]", "");
                if (!seen.add(cleaned.toLowerCase(Locale.ROOT))) {
                    continue;
                }
                int dot = cleaned.lastIndexOf('.');
                if (dot > 0) {
                    refs.add(new AuthzEvaluateRequest.TableRef(
                            null, cleaned.substring(0, dot), cleaned.substring(dot + 1)));
                } else {
                    refs.add(new AuthzEvaluateRequest.TableRef(null, null, cleaned));
                }
            }
        } catch (Exception ex) {
            log.warn("提取 SQL 表名失败，将以空表列表做鉴权", ex);
        }
        return refs;
    }

    /**
     * 单条语句解析结果。
     */
    public record ParseResult(String statementType, List<AuthzEvaluateRequest.TableRef> tables, String sql) {
    }
}
