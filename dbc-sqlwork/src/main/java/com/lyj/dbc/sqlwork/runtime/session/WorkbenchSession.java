package com.lyj.dbc.sqlwork.runtime.session;

import java.sql.Connection;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 工作台 SQL 会话：元数据 + 可选事务租约连接。
 */
public final class WorkbenchSession {

    private final String sessionId;
    private final Long userId;
    private final Long workspaceId;
    private volatile Long connectionId;
    private volatile String database;
    private volatile String schema;
    private volatile boolean manualMode;
    private final Instant createdAt;
    private volatile Instant lastActiveAt;

    /** 事务中独占连接；非 null 表示 inTransaction */
    private final AtomicReference<Connection> lease = new AtomicReference<>();

    public WorkbenchSession(String sessionId, Long userId, Long workspaceId, Long connectionId,
                            String database, String schema, boolean manualMode) {
        this.sessionId = sessionId;
        this.userId = userId;
        this.workspaceId = workspaceId;
        this.connectionId = connectionId;
        this.database = database;
        this.schema = schema;
        this.manualMode = manualMode;
        this.createdAt = Instant.now();
        this.lastActiveAt = this.createdAt;
    }

    public String getSessionId() {
        return sessionId;
    }

    public Long getUserId() {
        return userId;
    }

    public Long getWorkspaceId() {
        return workspaceId;
    }

    public Long getConnectionId() {
        return connectionId;
    }

    public void setConnectionId(Long connectionId) {
        this.connectionId = connectionId;
    }

    public String getDatabase() {
        return database;
    }

    public void setDatabase(String database) {
        this.database = database;
    }

    public String getSchema() {
        return schema;
    }

    public void setSchema(String schema) {
        this.schema = schema;
    }

    public boolean isManualMode() {
        return manualMode;
    }

    public void setManualMode(boolean manualMode) {
        this.manualMode = manualMode;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getLastActiveAt() {
        return lastActiveAt;
    }

    public void touch() {
        this.lastActiveAt = Instant.now();
    }

    public boolean inTransaction() {
        return lease.get() != null;
    }

    public Connection getLease() {
        return lease.get();
    }

    public void setLease(Connection connection) {
        lease.set(connection);
    }

    public Connection clearLease() {
        return lease.getAndSet(null);
    }
}
