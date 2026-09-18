package com.lyj.dbc.sqlwork.runtime.pool;

import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.ConnectionPingResult;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.dialect.DialectRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.Properties;

/**
 * 目标库短超时探活：一次性 JDBC，不占用连接池缓存。
 */
@Service
public class ConnectionProbeService {

    private static final Logger log = LoggerFactory.getLogger(ConnectionProbeService.class);

    /** 探活连接超时（秒） */
    private static final int CONNECT_TIMEOUT_SECONDS = 5;

    /** 探活语句超时（秒） */
    private static final int QUERY_TIMEOUT_SECONDS = 5;

    private final DialectRegistry dialectRegistry;

    public ConnectionProbeService(DialectRegistry dialectRegistry) {
        this.dialectRegistry = dialectRegistry;
    }

    public ConnectionPingResult ping(ConnectionMaterial material) {
        if (material == null) {
            throw BizException.badRequest("连接材料为空");
        }
        if (material.getJdbcUrl() == null || material.getJdbcUrl().isBlank()) {
            throw BizException.badRequest("连接缺少 jdbcUrl");
        }
        if (material.getUsername() == null || material.getUsername().isBlank()) {
            throw BizException.badRequest("连接缺少用户名");
        }
        String driver = material.getDriverClassName();
        if (driver == null || driver.isBlank()) {
            driver = dialectRegistry.require(material.getDbType()).defaultDriverClassName();
        }
        String probeSql = dialectRegistry.require(material.getDbType()).probeSql();

        long start = System.nanoTime();
        try {
            Class.forName(driver);
            Properties props = new Properties();
            props.setProperty("user", material.getUsername());
            props.setProperty("password", material.getPassword() == null ? "" : material.getPassword());
            // 常见驱动识别的超时键；未知键会被忽略
            props.setProperty("loginTimeout", String.valueOf(CONNECT_TIMEOUT_SECONDS));
            props.setProperty("connectTimeout", String.valueOf(CONNECT_TIMEOUT_SECONDS));
            props.setProperty("socketTimeout", String.valueOf(QUERY_TIMEOUT_SECONDS));

            DriverManager.setLoginTimeout(CONNECT_TIMEOUT_SECONDS);
            try (Connection conn = DriverManager.getConnection(material.getJdbcUrl(), props);
                 Statement st = conn.createStatement()) {
                st.setQueryTimeout(QUERY_TIMEOUT_SECONDS);
                st.execute(probeSql);
            }
            long ms = (System.nanoTime() - start) / 1_000_000L;
            return ConnectionPingResult.ok(ms);
        } catch (ClassNotFoundException e) {
            long ms = (System.nanoTime() - start) / 1_000_000L;
            log.warn("探活失败：驱动类不可用 driver={}", driver, e);
            return ConnectionPingResult.fail(ms, "驱动不可用: " + driver);
        } catch (Exception e) {
            long ms = (System.nanoTime() - start) / 1_000_000L;
            log.warn("探活失败 url={} user={}", material.getJdbcUrl(), material.getUsername(), e);
            String msg = e.getMessage();
            if (msg == null || msg.isBlank()) {
                msg = e.getClass().getSimpleName();
            }
            if (msg.length() > 240) {
                msg = msg.substring(0, 240);
            }
            return ConnectionPingResult.fail(ms, msg);
        }
    }
}
