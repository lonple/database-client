package com.lyj.dbc.sqlwork.runtime.jdbc;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.sql.SQLException;
import java.sql.Statement;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 按 cancelToken 登记进行中的 JDBC Statement，供 /execute/cancel 打断长查询。
 */
@Component
public class ExecuteCancelRegistry {

    private static final Logger log = LoggerFactory.getLogger(ExecuteCancelRegistry.class);

    private final Map<String, Statement> active = new ConcurrentHashMap<>();

    public void register(String cancelToken, Statement statement) {
        if (cancelToken == null || cancelToken.isBlank() || statement == null) {
            return;
        }
        Statement prev = active.put(cancelToken.trim(), statement);
        if (prev != null && prev != statement) {
            log.debug("cancelToken 覆盖旧 Statement: {}", cancelToken);
        }
    }

    public void unregister(String cancelToken) {
        if (cancelToken == null || cancelToken.isBlank()) {
            return;
        }
        active.remove(cancelToken.trim());
    }

    /**
     * @return true 若找到并已调用 Statement.cancel()
     */
    public boolean cancel(String cancelToken) {
        if (cancelToken == null || cancelToken.isBlank()) {
            return false;
        }
        Statement stmt = active.get(cancelToken.trim());
        if (stmt == null) {
            return false;
        }
        try {
            stmt.cancel();
            log.info("已取消执行 cancelToken={}", cancelToken);
            return true;
        } catch (SQLException ex) {
            log.warn("取消执行失败 cancelToken={}", cancelToken, ex);
            return false;
        }
    }
}
