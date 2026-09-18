package com.lyj.dbc.sqlwork.pipeline;

import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import com.lyj.dbc.sqlwork.api.dto.ExecuteRequest;
import com.lyj.dbc.sqlwork.api.vo.AuthzEvaluateResult;
import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.ExecuteResult;
import com.lyj.dbc.sqlwork.client.ManageClient;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import com.lyj.dbc.sqlwork.runtime.jdbc.SqlExecutor;
import com.lyj.dbc.sqlwork.runtime.pool.TargetDataSourceManager;
import com.lyj.dbc.sqlwork.runtime.session.SqlSessionManager;
import com.lyj.dbc.sqlwork.runtime.session.WorkbenchSession;
import com.lyj.dbc.sqlwork.security.LoginUser;
import com.lyj.dbc.sqlwork.security.SecurityUtils;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * SQL 执行管道：校验 → 拆分解析 → 逐句鉴权/执行（遇错停止）→ AuditStage 异步上报。
 * <p>
 * 手动事务：sessionId + manualMode 下，BEGIN 后租约独占连接直至 COMMIT/ROLLBACK。
 */
@Service
public class SqlPipeline {

    private static final Logger log = LoggerFactory.getLogger(SqlPipeline.class);
    private static final int SQL_PREVIEW_MAX = 200;

    private final SqlParseService parseService;
    private final ManageClient manageClient;
    private final TargetDataSourceManager dataSourceManager;
    private final SqlExecutor sqlExecutor;
    private final SqlworkProperties properties;
    private final AuditStage auditStage;
    private final SqlSessionManager sessionManager;

    public SqlPipeline(SqlParseService parseService, ManageClient manageClient,
                       TargetDataSourceManager dataSourceManager, SqlExecutor sqlExecutor,
                       SqlworkProperties properties, AuditStage auditStage,
                       SqlSessionManager sessionManager) {
        this.parseService = parseService;
        this.manageClient = manageClient;
        this.dataSourceManager = dataSourceManager;
        this.sqlExecutor = sqlExecutor;
        this.properties = properties;
        this.auditStage = auditStage;
        this.sessionManager = sessionManager;
    }

    public ExecuteResult execute(ExecuteRequest request) {
        LoginUser user = SecurityUtils.requireUser();
        String authHeader = SecurityUtils.requireAuthorizationHeader();
        if (request.getWorkspaceId() == null || request.getConnectionId() == null) {
            throw BizException.badRequest("workspaceId / connectionId 不能为空");
        }
        if (request.getSql() == null || request.getSql().isBlank()) {
            throw BizException.badRequest("sql 不能为空");
        }

        WorkbenchSession session = null;
        if (StringUtils.hasText(request.getSessionId())) {
            session = sessionManager.requireOwned(request.getSessionId().trim(), user.getUserId());
            if (!Objects.equals(session.getWorkspaceId(), request.getWorkspaceId())) {
                throw BizException.badRequest("session 与 workspaceId 不匹配");
            }
            if (!Objects.equals(session.getConnectionId(), request.getConnectionId())) {
                throw BizException.badRequest("session 与 connectionId 不匹配，请先更新会话或切换连接");
            }
        }

        int maxRows = resolveMaxRows(request.getMaxRows());
        ConnectionMaterial material = manageClient.getMaterial(request.getConnectionId(), authHeader);
        List<SqlParseService.ParseResult> parsedList = parseService.parseBatch(request.getSql(), material.getDbType());

        String effectiveDb = StringUtils.hasText(request.getDatabase())
                ? request.getDatabase()
                : (session == null ? null : session.getDatabase());
        String effectiveSchema = StringUtils.hasText(request.getSchema())
                ? request.getSchema()
                : (session == null ? null : session.getSchema());

        material = applyDatabaseOverride(material, effectiveDb);
        DataSource ds = dataSourceManager.get(material);

        SqlExecuteContext auditCtx = SqlExecuteContext.builder()
                .batchId(UUID.randomUUID().toString())
                .operatorUserId(user.getUserId())
                .operatorUsername(user.getUsername())
                .clientIp(resolveClientIp())
                .workspaceId(request.getWorkspaceId())
                .connectionId(request.getConnectionId())
                .connectionName(material.getName())
                .dbType(material.getDbType())
                .statements(new ArrayList<>())
                .build();

        List<ExecuteResult.StatementResult> statements = new ArrayList<>(parsedList.size());
        boolean stoppedOnError = false;
        String batchMessage = "ok";
        long batchStart = System.currentTimeMillis();
        boolean schemaAppliedOnLease = session != null && session.inTransaction();

        try {
            for (int i = 0; i < parsedList.size(); i++) {
                SqlParseService.ParseResult parsed = parsedList.get(i);
                int index = i + 1;
                String stmtType = parsed.statementType();
                String preview = previewSql(parsed.sql());

                AuthzEvaluateResult authz = authorizeStatement(
                        user, request, parsed, stmtType, authHeader);
                if (!authz.isAllowed()) {
                    String msg = authz.getMessage() == null ? "无执行权限" : authz.getMessage();
                    statements.add(failedStatement(index, preview, stmtType, msg, authz));
                    auditCtx.getStatements().add(SqlExecuteContext.StatementAuditItem.fromAuthzFail(
                            index, parsed.sql(), stmtType, msg, authz));
                    stoppedOnError = true;
                    batchMessage = "第 " + index + " 条被拒绝: " + msg;
                    break;
                }

                long stmtStart = System.currentTimeMillis();
                try {
                    ExecuteResult.StatementResult one = dispatchExecute(
                            session, ds, parsed, stmtType, maxRows, effectiveSchema, schemaAppliedOnLease);
                    if (session != null && session.inTransaction()) {
                        schemaAppliedOnLease = true;
                    }
                    one.setIndex(index);
                    one.setSqlPreview(preview);
                    applyPolicyMeta(one, authz);
                    statements.add(one);
                    auditCtx.getStatements().add(SqlExecuteContext.StatementAuditItem.builder()
                            .statementIndex(index)
                            .sqlText(parsed.sql())
                            .statementType(stmtType)
                            .success(true)
                            .elapsedMs(System.currentTimeMillis() - stmtStart)
                            .message(one.getMessage())
                            .globalPolicyAction(authz.getGlobalPolicyAction())
                            .globalPolicyName(authz.getGlobalPolicyName())
                            .build());
                } catch (BizException ex) {
                    String msg = ex.getMessage() == null ? "执行失败" : ex.getMessage();
                    long elapsed = System.currentTimeMillis() - stmtStart;
                    statements.add(failedStatement(index, preview, stmtType, msg, authz));
                    auditCtx.getStatements().add(SqlExecuteContext.StatementAuditItem.builder()
                            .statementIndex(index)
                            .sqlText(parsed.sql())
                            .statementType(stmtType)
                            .success(false)
                            .elapsedMs(elapsed)
                            .message(msg)
                            .globalPolicyAction(authz.getGlobalPolicyAction())
                            .globalPolicyName(authz.getGlobalPolicyName())
                            .build());
                    stoppedOnError = true;
                    batchMessage = "第 " + index + " 条失败: " + msg;
                    break;
                }
            }
        } finally {
            auditStage.flush(auditCtx);
        }

        int successCount = (int) statements.stream().filter(ExecuteResult.StatementResult::isSuccess).count();
        if (!stoppedOnError) {
            batchMessage = successCount == parsedList.size()
                    ? "全部成功（" + successCount + " 条）"
                    : "完成";
        }

        boolean manual = session != null && session.isManualMode();
        boolean inTx = session != null && session.inTransaction();
        return ExecuteResult.builder()
                .totalCount(parsedList.size())
                .successCount(successCount)
                .stoppedOnError(stoppedOnError)
                .message(batchMessage)
                .elapsedMs(System.currentTimeMillis() - batchStart)
                .sessionId(session == null ? null : session.getSessionId())
                .manualMode(manual)
                .inTransaction(inTx)
                .statements(statements)
                .build();
    }

    private AuthzEvaluateResult authorizeStatement(LoginUser user, ExecuteRequest request,
                                                   SqlParseService.ParseResult parsed,
                                                   String stmtType, String authHeader) {
        // 事务控制：具备连接访问权即可（WORKBENCH：任意 SQL ops）
        if (SqlParseService.isTxControl(stmtType)) {
            AuthzEvaluateRequest authzReq = new AuthzEvaluateRequest(
                    user.getUserId(),
                    request.getWorkspaceId(),
                    request.getConnectionId(),
                    null,
                    Collections.emptyList(),
                    "WORKBENCH",
                    request.getSessionId(),
                    null
            );
            return manageClient.evaluate(authzReq, authHeader);
        }
        AuthzEvaluateRequest authzReq = new AuthzEvaluateRequest(
                user.getUserId(),
                request.getWorkspaceId(),
                request.getConnectionId(),
                stmtType,
                parsed.tables(),
                "EXECUTE",
                request.getSessionId(),
                null
        );
        return manageClient.evaluate(authzReq, authHeader);
    }

    private ExecuteResult.StatementResult dispatchExecute(WorkbenchSession session,
                                                          DataSource ds,
                                                          SqlParseService.ParseResult parsed,
                                                          String stmtType,
                                                          int maxRows,
                                                          String schema,
                                                          boolean schemaAlreadyApplied) {
        String type = stmtType == null ? "" : stmtType.trim().toUpperCase();
        boolean manual = session != null && session.isManualMode();

        if ("BEGIN".equals(type)) {
            if (!manual) {
                throw BizException.badRequest("请先切换到「手动提交」模式再执行 BEGIN");
            }
            if (session.inTransaction()) {
                throw BizException.badRequest("当前会话已在事务中，请先 COMMIT 或 ROLLBACK");
            }
            Connection conn = sqlExecutor.borrowForTransaction(ds, schema);
            try {
                ExecuteResult.StatementResult one = sqlExecutor.executeOnConnection(
                        conn, parsed.sql(), stmtType, maxRows, null, false);
                sessionManager.bindLease(session, conn);
                one.setMessage("事务已开启");
                return one;
            } catch (RuntimeException ex) {
                silentClose(conn);
                throw ex;
            }
        }

        if ("COMMIT".equals(type) || "ROLLBACK".equals(type)) {
            if (session == null || !session.inTransaction()) {
                throw BizException.badRequest("当前不在事务中，无法 " + type);
            }
            Connection lease = session.getLease();
            try {
                ExecuteResult.StatementResult one = sqlExecutor.executeOnConnection(
                        lease, parsed.sql(), stmtType, maxRows, null, false);
                // SQL 已提交/回滚，释放租约时不再 rollback
                sessionManager.releaseLease(session, false);
                one.setMessage("COMMIT".equals(type) ? "事务已提交" : "事务已回滚");
                return one;
            } catch (RuntimeException ex) {
                // 失败时保留租约，由用户重试或关 Tab 回滚
                throw ex;
            }
        }

        if (session != null && session.inTransaction()) {
            Connection lease = session.getLease();
            if (lease == null) {
                throw BizException.badRequest("事务租约丢失，请重新 BEGIN");
            }
            return sqlExecutor.executeOnConnection(
                    lease, parsed.sql(), stmtType, maxRows, schema, !schemaAlreadyApplied);
        }

        return sqlExecutor.execute(ds, parsed.sql(), stmtType, maxRows, schema);
    }

    private static void silentClose(Connection conn) {
        if (conn == null) {
            return;
        }
        try {
            conn.rollback();
        } catch (SQLException e) {
            // ignore
        }
        try {
            conn.close();
        } catch (SQLException e) {
            // ignore
        }
    }

    private static String resolveClientIp() {
        try {
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs == null) {
                return null;
            }
            HttpServletRequest request = attrs.getRequest();
            String xff = request.getHeader("X-Forwarded-For");
            if (xff != null && !xff.isBlank()) {
                return xff.split(",")[0].trim();
            }
            String realIp = request.getHeader("X-Real-IP");
            if (realIp != null && !realIp.isBlank()) {
                return realIp.trim();
            }
            return request.getRemoteAddr();
        } catch (Exception e) {
            log.debug("解析客户端 IP 失败", e);
            return null;
        }
    }

    private static void applyPolicyMeta(ExecuteResult.StatementResult one, AuthzEvaluateResult authz) {
        String action = authz.getGlobalPolicyAction();
        one.setGlobalPolicyAction(action);
        one.setGlobalPolicyName(authz.getGlobalPolicyName());
        if (action != null && "ALERT".equalsIgnoreCase(action)) {
            one.setSeverity("WARN");
            String policy = authz.getGlobalPolicyName() == null ? "全局告警" : authz.getGlobalPolicyName();
            String base = one.getMessage() == null || "ok".equals(one.getMessage()) ? "" : one.getMessage() + "；";
            one.setMessage(base + "告警策略命中: " + policy);
        } else {
            one.setSeverity("SUCCESS");
        }
    }

    private static ExecuteResult.StatementResult failedStatement(int index, String preview,
                                                                  String statementType, String message,
                                                                  AuthzEvaluateResult authz) {
        return ExecuteResult.StatementResult.builder()
                .index(index)
                .sqlPreview(preview)
                .statementType(statementType)
                .columns(Collections.emptyList())
                .rows(Collections.emptyList())
                .rowCount(0)
                .truncated(false)
                .elapsedMs(0)
                .affectedRows(null)
                .success(false)
                .message(message)
                .severity("ERROR")
                .globalPolicyAction(authz == null ? null : authz.getGlobalPolicyAction())
                .globalPolicyName(authz == null ? null : authz.getGlobalPolicyName())
                .denyType(authz == null ? null : authz.getDenyType())
                .denyObjects(authz == null ? null : authz.getDenyObjects())
                .missingOps(authz == null ? null : authz.getMissingOps())
                .grantedOps(authz == null ? null : authz.getGrantedOps())
                .build();
    }

    private static String previewSql(String sql) {
        if (sql == null) {
            return "";
        }
        String oneLine = sql.replaceAll("\\s+", " ").trim();
        if (oneLine.length() <= SQL_PREVIEW_MAX) {
            return oneLine;
        }
        return oneLine.substring(0, SQL_PREVIEW_MAX) + "…";
    }

    private ConnectionMaterial applyDatabaseOverride(ConnectionMaterial material, String database) {
        if (database == null || database.isBlank() || material.getHost() == null || material.getPort() == null) {
            return material;
        }
        String db = database.trim();
        if (!db.matches("[A-Za-z0-9_\\-]+")) {
            throw BizException.badRequest("非法 database 名称");
        }
        String dbType = material.getDbType() == null ? "" : material.getDbType().trim().toUpperCase();
        String jdbcUrl;
        if (dbType.startsWith("MYSQL") || "MARIADB".equals(dbType)) {
            jdbcUrl = "jdbc:mysql://" + material.getHost() + ":" + material.getPort() + "/" + db
                    + "?useSSL=false&allowPublicKeyRetrieval=true";
        } else if ("ORACLE".equals(dbType)) {
            jdbcUrl = "jdbc:oracle:thin:@" + material.getHost() + ":" + material.getPort() + "/" + db;
        } else if ("SQLSERVER".equals(dbType)) {
            jdbcUrl = "jdbc:sqlserver://" + material.getHost() + ":" + material.getPort() + ";databaseName=" + db;
        } else {
            jdbcUrl = "jdbc:postgresql://" + material.getHost() + ":" + material.getPort() + "/" + db;
        }
        return new ConnectionMaterial(
                material.getConnectionId(),
                material.getName(),
                material.getDbType(),
                jdbcUrl,
                material.getUsername(),
                material.getPassword(),
                material.getDriverClassName(),
                db,
                material.getHost(),
                material.getPort()
        );
    }

    private int resolveMaxRows(Integer requested) {
        int def = properties.getExecuteMaxRows();
        int cap = properties.getExecuteMaxRowsCap();
        int value = requested == null ? def : requested;
        if (value <= 0) {
            value = def;
        }
        return Math.min(value, cap);
    }
}
