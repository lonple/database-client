package com.lyj.dbc.sqlwork.dialect;

import com.lyj.dbc.sqlwork.common.BizException;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * 按 DbType / 字符串解析并获取方言实现。
 */
@Component
public class DialectRegistry {

    private final Map<DbType, DbDialect> byType = new EnumMap<>(DbType.class);

    public DialectRegistry(List<DbDialect> dialects) {
        for (DbDialect dialect : dialects) {
            byType.put(dialect.dbType(), dialect);
        }
    }

    public DbDialect require(DbType dbType) {
        DbDialect dialect = byType.get(dbType);
        if (dialect == null) {
            throw BizException.badRequest("不支持的数据库类型: " + dbType);
        }
        return dialect;
    }

    public DbDialect require(String dbType) {
        try {
            return require(DbType.from(dbType));
        } catch (IllegalArgumentException ex) {
            throw BizException.badRequest("不支持的数据库类型: " + dbType);
        }
    }
}
