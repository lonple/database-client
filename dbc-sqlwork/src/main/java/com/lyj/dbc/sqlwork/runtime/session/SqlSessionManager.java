package com.lyj.dbc.sqlwork.runtime.session;

import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.SQLException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 工作台会话与事务连接租约管理。
 * <p>
 * 手动模式：用户执行 BEGIN 后独占连接，直至 COMMIT/ROLLBACK/关会话/超时。
 */
@Service
public class SqlSessionManager {

    private static final Logger log = LoggerFactory.getLogger(SqlSessionManager.class);

    private final ConcurrentHashMap<String, WorkbenchSession> sessions = new ConcurrentHashMap<>();
    private final SqlworkProperties properties;

    public SqlSessionManager(SqlworkProperties properties) {
        this.properties = properties;
    }

    public WorkbenchSession create(Long userId, Long workspaceId, Long connectionId,
                                   String database, String schema, boolean manualMode) {
        int max = Math.max(1, properties.getSessionMaxPerUser());
        long owned = sessions.values().stream().filter(s -> Objects.equals(s.getUserId(), userId)).count();
        if (owned >= max) {
            throw BizException.badRequest("每用户最多 " + max + " 个工作台会话，请先关闭闲置会话");
        }
        String id = "wsess-" + UUID.randomUUID();
        WorkbenchSession session = new WorkbenchSession(
                id, userId, workspaceId, connectionId, database, schema, manualMode);
        sessions.put(id, session);
        log.info("创建工作台会话 sessionId={} userId={} manual={}", id, userId, manualMode);
        return session;
    }

    public WorkbenchSession requireOwned(String sessionId, Long userId) {
        if (sessionId == null || sessionId.isBlank()) {
            throw BizException.badRequest("sessionId 不能为空");
        }
        WorkbenchSession session = sessions.get(sessionId);
        if (session == null) {
            throw BizException.notFound("会话不存在或已过期，请重新打开工作台 Tab");
        }
        if (!Objects.equals(session.getUserId(), userId)) {
            throw BizException.forbidden("无权使用该会话");
        }
        session.touch();
        return session;
    }

    public WorkbenchSession heartbeat(String sessionId, Long userId) {
        return requireOwned(sessionId, userId);
    }

    public WorkbenchSession update(String sessionId, Long userId, Long connectionId,
                                   String database, String schema, Boolean manualMode) {
        WorkbenchSession session = requireOwned(sessionId, userId);
        if (session.inTransaction()) {
            if (connectionId != null && !Objects.equals(connectionId, session.getConnectionId())) {
                throw BizException.badRequest("事务进行中不能切换连接，请先 COMMIT 或 ROLLBACK");
            }
            if (database != null && !Objects.equals(blankToNull(database), blankToNull(session.getDatabase()))) {
                throw BizException.badRequest("事务进行中不能切换库，请先 COMMIT 或 ROLLBACK");
            }
            if (Boolean.FALSE.equals(manualMode)) {
                throw BizException.badRequest("事务进行中不能关闭手动提交，请先 COMMIT 或 ROLLBACK");
            }
        }
        if (connectionId != null) {
            session.setConnectionId(connectionId);
        }
        if (database != null) {
            session.setDatabase(blankToNull(database));
        }
        if (schema != null) {
            session.setSchema(blankToNull(schema));
        }
        if (manualMode != null) {
            session.setManualMode(manualMode);
        }
        session.touch();
        return session;
    }

    public void close(String sessionId, Long userId) {
        WorkbenchSession session = sessions.remove(sessionId);
        if (session == null) {
            return;
        }
        if (!Objects.equals(session.getUserId(), userId)) {
            sessions.put(sessionId, session);
            throw BizException.forbidden("无权关闭该会话");
        }
        releaseLease(session, true);
        log.info("关闭工作台会话 sessionId={} userId={}", sessionId, userId);
    }

    /**
     * 绑定事务租约（BEGIN 成功后调用）。
     */
    public void bindLease(WorkbenchSession session, Connection connection) {
        Connection old = session.getLease();
        if (old != null && old != connection) {
            silentRollbackAndClose(old);
        }
        session.setLease(connection);
        session.touch();
    }

    /**
     * 释放租约；rollbackIfNeeded 为 true 时先 rollback。
     */
    public void releaseLease(WorkbenchSession session, boolean rollbackIfNeeded) {
        Connection conn = session.clearLease();
        if (conn == null) {
            return;
        }
        try {
            if (rollbackIfNeeded) {
                try {
                    if (!conn.getAutoCommit()) {
                        conn.rollback();
                    }
                } catch (SQLException e) {
                    log.warn("释放租约时 rollback 失败 sessionId={}", session.getSessionId(), e);
                }
            }
            try {
                conn.setAutoCommit(true);
            } catch (SQLException e) {
                log.debug("恢复 autoCommit 失败 sessionId={}", session.getSessionId(), e);
            }
            conn.close();
        } catch (SQLException e) {
            log.warn("关闭租约连接失败 sessionId={}", session.getSessionId(), e);
        }
        session.touch();
    }

    @Scheduled(fixedDelayString = "${dbc.sqlwork.session-cleanup-interval-ms:30000}")
    public void cleanupExpired() {
        Instant now = Instant.now();
        Duration idleTtl = Duration.ofSeconds(Math.max(60, properties.getSessionIdleTtlSeconds()));
        Duration txIdleTtl = Duration.ofSeconds(Math.max(60, properties.getSessionTransactionIdleTtlSeconds()));
        List<String> toRemove = new ArrayList<>();
        for (Map.Entry<String, WorkbenchSession> e : sessions.entrySet()) {
            WorkbenchSession s = e.getValue();
            Duration idle = Duration.between(s.getLastActiveAt(), now);
            if (s.inTransaction()) {
                if (idle.compareTo(txIdleTtl) > 0) {
                    log.warn("事务会话闲置超时，回滚并释放 sessionId={} userId={} idleSec={}",
                            s.getSessionId(), s.getUserId(), idle.toSeconds());
                    releaseLease(s, true);
                    toRemove.add(e.getKey());
                }
            } else if (idle.compareTo(idleTtl) > 0) {
                log.info("会话闲置超时，清理 sessionId={} userId={}", s.getSessionId(), s.getUserId());
                toRemove.add(e.getKey());
            }
        }
        for (String id : toRemove) {
            WorkbenchSession removed = sessions.remove(id);
            if (removed != null) {
                releaseLease(removed, true);
            }
        }
    }

    @PreDestroy
    public void shutdown() {
        for (WorkbenchSession s : sessions.values()) {
            releaseLease(s, true);
        }
        sessions.clear();
    }

    private static void silentRollbackAndClose(Connection conn) {
        try {
            if (!conn.getAutoCommit()) {
                conn.rollback();
            }
        } catch (SQLException e) {
            // ignore
        }
        try {
            conn.close();
        } catch (SQLException e) {
            // ignore
        }
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s.trim();
    }
}
