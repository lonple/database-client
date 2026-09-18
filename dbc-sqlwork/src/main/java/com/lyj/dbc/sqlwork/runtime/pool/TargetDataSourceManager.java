package com.lyj.dbc.sqlwork.runtime.pool;

import com.alibaba.druid.pool.DruidDataSource;
import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import com.lyj.dbc.sqlwork.dialect.DialectRegistry;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 按 connectionId + jdbcUrl 缓存目标库 Druid 连接池（支持切换库）。
 * <p>
 * 建连失败时快速失败并剔除坏池，避免 CreateConnectionThread 疯狂重试刷屏。
 */
@Component
public class TargetDataSourceManager {

    private static final Logger log = LoggerFactory.getLogger(TargetDataSourceManager.class);

    private final SqlworkProperties properties;
    private final DialectRegistry dialectRegistry;
    private final ConcurrentHashMap<String, DruidDataSource> cache = new ConcurrentHashMap<>();

    public TargetDataSourceManager(SqlworkProperties properties, DialectRegistry dialectRegistry) {
        this.properties = properties;
        this.dialectRegistry = dialectRegistry;
    }

    public DataSource get(ConnectionMaterial material) {
        if (material == null || material.getConnectionId() == null) {
            throw BizException.badRequest("connectionId 不能为空");
        }
        if (material.getJdbcUrl() == null || material.getJdbcUrl().isBlank()) {
            throw BizException.badRequest("连接缺少 jdbcUrl");
        }
        String key = material.getConnectionId() + "|" + material.getJdbcUrl();
        return cache.computeIfAbsent(key, k -> createPool(material));
    }

    /**
     * 借连接失败或探活失败后调用：关闭并移除该连接相关池，停止后台建连重试。
     */
    public void evict(Long connectionId) {
        if (connectionId == null) {
            return;
        }
        String prefix = connectionId + "|";
        for (Map.Entry<String, DruidDataSource> e : cache.entrySet()) {
            if (e.getKey().startsWith(prefix)) {
                DruidDataSource ds = cache.remove(e.getKey());
                closeQuietly(e.getKey(), ds);
            }
        }
    }

    @PreDestroy
    public void shutdown() {
        for (Map.Entry<String, DruidDataSource> e : cache.entrySet()) {
            closeQuietly(e.getKey(), e.getValue());
        }
        cache.clear();
    }

    private DruidDataSource createPool(ConnectionMaterial material) {
        String driver = material.getDriverClassName();
        if (driver == null || driver.isBlank()) {
            driver = dialectRegistry.require(material.getDbType()).defaultDriverClassName();
        }
        String probeSql = dialectRegistry.require(material.getDbType()).probeSql();
        int maxActive = Math.max(1, properties.getPoolMaxSize());

        DruidDataSource ds = new DruidDataSource();
        ds.setName("sqlwork-" + material.getConnectionId() + "-" + Math.abs(material.getJdbcUrl().hashCode()));
        ds.setUrl(material.getJdbcUrl());
        ds.setUsername(material.getUsername());
        ds.setPassword(material.getPassword());
        ds.setDriverClassName(driver);
        ds.setInitialSize(0);
        ds.setMinIdle(0);
        ds.setMaxActive(maxActive);
        ds.setMaxWait(5_000L);
        // 建连失败后不要无限重试刷 ERROR 栈
        ds.setFailFast(true);
        ds.setConnectionErrorRetryAttempts(0);
        ds.setBreakAfterAcquireFailure(true);
        ds.setTimeBetweenConnectErrorMillis(60_000L);
        ds.setTimeBetweenEvictionRunsMillis(60_000L);
        ds.setMinEvictableIdleTimeMillis(60_000L);
        ds.setMaxEvictableIdleTimeMillis(300_000L);
        ds.setValidationQuery(probeSql);
        ds.setTestWhileIdle(true);
        ds.setTestOnBorrow(false);
        ds.setTestOnReturn(false);
        try {
            ds.init();
        } catch (Exception ex) {
            ds.close();
            log.warn("创建目标库连接池失败 connectionId={} url={}",
                    material.getConnectionId(), material.getJdbcUrl(), ex);
            throw BizException.badRequest("创建目标库连接池失败: " + ex.getMessage());
        }
        return ds;
    }

    private void closeQuietly(String key, DruidDataSource ds) {
        if (ds == null) {
            return;
        }
        try {
            ds.close();
        } catch (Exception ex) {
            log.warn("关闭连接池失败 key={}", key, ex);
        }
    }
}
