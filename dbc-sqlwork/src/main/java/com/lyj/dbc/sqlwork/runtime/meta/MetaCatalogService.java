package com.lyj.dbc.sqlwork.runtime.meta;

import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.MetaTreeVO;
import com.lyj.dbc.sqlwork.api.vo.TablePageVO;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.dialect.DbDialect;
import com.lyj.dbc.sqlwork.dialect.DialectRegistry;
import com.lyj.dbc.sqlwork.runtime.pool.TargetDataSourceManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * 目标库元数据目录服务（经方言 SPI）。
 */
@Service
public class MetaCatalogService {

    private static final Logger log = LoggerFactory.getLogger(MetaCatalogService.class);

    private final TargetDataSourceManager dataSourceManager;
    private final DialectRegistry dialectRegistry;

    public MetaCatalogService(TargetDataSourceManager dataSourceManager, DialectRegistry dialectRegistry) {
        this.dataSourceManager = dataSourceManager;
        this.dialectRegistry = dialectRegistry;
    }

    public List<String> listDatabases(ConnectionMaterial material) {
        DbDialect dialect = dialectRegistry.require(material.getDbType());
        DataSource ds = dataSourceManager.get(material);
        try (Connection conn = ds.getConnection()) {
            return dialect.listDatabases(conn);
        } catch (SQLException ex) {
            dataSourceManager.evict(material.getConnectionId());
            log.warn("列出数据库失败 connectionId={} url={}", material.getConnectionId(), material.getJdbcUrl(), ex);
            throw BizException.badRequest("列出数据库失败: " + summarize(ex));
        }
    }

    public List<String> listSchemas(ConnectionMaterial material, String database) {
        DbDialect dialect = dialectRegistry.require(material.getDbType());
        DataSource ds = dataSourceManager.get(material);
        try (Connection conn = ds.getConnection()) {
            return dialect.listSchemas(conn, database);
        } catch (SQLException ex) {
            dataSourceManager.evict(material.getConnectionId());
            log.warn("列出 schema 失败 connectionId={}", material.getConnectionId(), ex);
            throw BizException.badRequest("列出 schema 失败: " + summarize(ex));
        }
    }

    public TablePageVO listTables(ConnectionMaterial material, String database, String schema,
                                  String keyword, int page, int size) {
        return listTables(material, database, schema, keyword, null, page, size);
    }

    /**
     * @param nameAllowlist 非空时下推表名 IN；用于表级授权，避免先扫全 schema 再内存过滤
     */
    public TablePageVO listTables(ConnectionMaterial material, String database, String schema,
                                  String keyword, Collection<String> nameAllowlist,
                                  int page, int size) {
        DbDialect dialect = dialectRegistry.require(material.getDbType());
        DataSource ds = dataSourceManager.get(material);
        try (Connection conn = ds.getConnection()) {
            DbDialect.TablePage pageResult = dialect.listTables(
                    conn, database, schema, keyword, nameAllowlist, page, size);
            List<TablePageVO.TableItemVO> items = pageResult.items().stream()
                    .map(t -> new TablePageVO.TableItemVO(t.schema(), t.name(), t.objectType()))
                    .toList();
            return TablePageVO.builder()
                    .items(items)
                    .total(pageResult.total())
                    .page(Math.max(page, 1))
                    .size(Math.max(size, 1))
                    .build();
        } catch (SQLException ex) {
            dataSourceManager.evict(material.getConnectionId());
            log.warn("列出表失败 connectionId={}", material.getConnectionId(), ex);
            throw BizException.badRequest("列出表失败: " + summarize(ex));
        }
    }

    private static String summarize(SQLException ex) {
        String msg = ex.getMessage();
        if (msg == null || msg.isBlank()) {
            return ex.getClass().getSimpleName();
        }
        if (msg.length() > 200) {
            return msg.substring(0, 200);
        }
        return msg;
    }

    /**
     * 浅树：库 → schema → 表（每 schema 最多取 size 张表，供工作台首屏）。
     * 调用方应先按授权收窄库/模式，再对本方法结果做表过滤或下推。
     */
    public MetaTreeVO buildShallowTree(ConnectionMaterial material, int tablesPerSchema) {
        List<String> databases = listDatabases(material);
        List<MetaTreeVO.DatabaseNode> dbNodes = new ArrayList<>();
        int limit = Math.max(tablesPerSchema, 1);
        for (String db : databases) {
            List<String> schemas = listSchemas(material, db);
            List<MetaTreeVO.SchemaNode> schemaNodes = new ArrayList<>();
            for (String schema : schemas) {
                TablePageVO tables = listTables(material, db, schema, null, 1, limit);
                List<MetaTreeVO.TableNode> tableNodes = tables.getItems().stream()
                        .map(t -> new MetaTreeVO.TableNode(t.getName(), t.getObjectType()))
                        .toList();
                schemaNodes.add(new MetaTreeVO.SchemaNode(schema, new ArrayList<>(tableNodes)));
            }
            dbNodes.add(new MetaTreeVO.DatabaseNode(db, schemaNodes));
        }
        return MetaTreeVO.builder().databases(dbNodes).build();
    }
}
