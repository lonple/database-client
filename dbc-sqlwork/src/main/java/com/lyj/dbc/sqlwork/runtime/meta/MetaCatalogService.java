package com.lyj.dbc.sqlwork.runtime.meta;

import com.lyj.dbc.sqlwork.api.vo.ColumnVO;
import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.MetaTreeVO;
import com.lyj.dbc.sqlwork.api.vo.TableColumnsVO;
import com.lyj.dbc.sqlwork.api.vo.TableDocVO;
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
                    .map(t -> new TablePageVO.TableItemVO(
                            t.schema(), t.name(), t.objectType(), t.comment()))
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

    public List<ColumnVO> listColumns(ConnectionMaterial material, String database, String schema, String table) {
        if (table == null || table.isBlank()) {
            throw BizException.badRequest("table 不能为空");
        }
        DbDialect dialect = dialectRegistry.require(material.getDbType());
        DataSource ds = dataSourceManager.get(material);
        try (Connection conn = ds.getConnection()) {
            return mapColumns(dialect.listColumns(conn, database, schema, table));
        } catch (SQLException ex) {
            dataSourceManager.evict(material.getConnectionId());
            log.warn("列出列失败 connectionId={} table={}", material.getConnectionId(), table, ex);
            throw BizException.badRequest("列出列失败: " + summarize(ex));
        }
    }

    /**
     * 同连接复用一次 JDBC Connection，批量拉多表列；单表失败写入 error，不中断整批。
     */
    public List<TableColumnsVO> listColumnsBatch(
            ConnectionMaterial material,
            String database,
            String schema,
            List<String> tables) {
        if (tables == null || tables.isEmpty()) {
            return List.of();
        }
        DbDialect dialect = dialectRegistry.require(material.getDbType());
        DataSource ds = dataSourceManager.get(material);
        List<TableColumnsVO> out = new ArrayList<>();
        try (Connection conn = ds.getConnection()) {
            for (String raw : tables) {
                String table = raw == null ? "" : raw.trim();
                if (table.isEmpty()) {
                    continue;
                }
                try {
                    List<ColumnVO> cols = mapColumns(dialect.listColumns(conn, database, schema, table));
                    out.add(TableColumnsVO.builder()
                            .table(table)
                            .schema(schema)
                            .columns(cols)
                            .build());
                } catch (Exception ex) {
                    log.warn(
                            "批量列查询单表失败 connectionId={} table={}",
                            material.getConnectionId(),
                            table,
                            ex);
                    out.add(TableColumnsVO.builder()
                            .table(table)
                            .schema(schema)
                            .columns(List.of())
                            .error(summarize(ex))
                            .build());
                }
            }
            return out;
        } catch (SQLException ex) {
            dataSourceManager.evict(material.getConnectionId());
            log.warn("批量列出列失败 connectionId={}", material.getConnectionId(), ex);
            throw BizException.badRequest("批量列出列失败: " + summarize(ex));
        }
    }


    private static List<ColumnVO> mapColumns(List<? extends DbDialect.ColumnItem> items) {
        return items.stream()
                .map(c -> ColumnVO.builder()
                        .name(c.name())
                        .dataType(c.dataType())
                        .nullable(c.nullable())
                        .comment(c.comment())
                        .ordinal(c.ordinal())
                        .build())
                .toList();
    }

    /**
     * 单表文档：英文表名 + 中文说明 + 字段列表，并生成 Markdown。
     */
    public TableDocVO tableDoc(ConnectionMaterial material, String database, String schema, String table) {
        if (table == null || table.isBlank()) {
            throw BizException.badRequest("table 不能为空");
        }
        String tableName = table.trim();
        TablePageVO page = listTables(material, database, schema, null, List.of(tableName), 1, 1);
        TablePageVO.TableItemVO meta = page.getItems().stream()
                .filter(t -> tableName.equalsIgnoreCase(t.getName()))
                .findFirst()
                .orElse(null);
        if (meta == null) {
            throw BizException.badRequest("未找到表: " + tableName);
        }
        List<ColumnVO> columns = listColumns(material, database, schema, meta.getName());
        String comment = meta.getComment() == null ? "" : meta.getComment().trim();
        return TableDocVO.builder()
                .name(meta.getName())
                .schema(meta.getSchema())
                .objectType(meta.getObjectType())
                .comment(comment.isEmpty() ? null : comment)
                .columns(columns)
                .markdown(toMarkdown(meta.getName(), comment, columns))
                .build();
    }

    static String toMarkdown(String tableName, String tableComment, List<ColumnVO> columns) {
        StringBuilder md = new StringBuilder();
        md.append("# ").append(tableName == null ? "" : tableName).append("\n\n");
        if (tableComment != null && !tableComment.isBlank()) {
            md.append(tableComment.trim()).append("\n\n");
        }
        md.append("## 字段列表\n\n");
        md.append("| 字段名 | 字段描述 | 字段类型 | 是否必须 |\n");
        md.append("| --- | --- | --- | --- |\n");
        if (columns != null) {
            for (ColumnVO c : columns) {
                String desc = c.getComment() == null || c.getComment().isBlank() ? "—" : c.getComment().trim();
                String type = c.getDataType() == null || c.getDataType().isBlank() ? "—" : c.getDataType();
                String required = c.isNullable() ? "否" : "是";
                md.append("| ").append(escapeCell(c.getName()))
                        .append(" | ").append(escapeCell(desc))
                        .append(" | ").append(escapeCell(type))
                        .append(" | ").append(required)
                        .append(" |\n");
            }
        }
        return md.toString();
    }

    private static String escapeCell(String raw) {
        if (raw == null) {
            return "";
        }
        return raw.replace("|", "\\|").replace("\n", " ");
    }

    private static String summarize(Throwable ex) {
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
