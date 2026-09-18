package com.lyj.dbc.sqlwork.runtime.meta;

import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import com.lyj.dbc.sqlwork.api.vo.AuthzEvaluateResult;
import com.lyj.dbc.sqlwork.api.vo.ObjectFilter;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * 根据 objectFilter 规划元数据查询策略，避免「先全量/分页拉目标库再内存过滤」。
 * <p>
 * 表级白名单走 name IN 下推；库/模式若可从授权推导则跳过 catalog 全扫。
 */
public final class MetaVisibilityPlanner {

    public static final String LEVEL_DATABASE = "DATABASE";
    public static final String LEVEL_SCHEMA = "SCHEMA";
    public static final String LEVEL_TABLE = "TABLE";

    /** 单次 IN 下推上限，超出则分批查询后合并分页 */
    public static final int NAME_IN_BATCH = 500;

    private MetaVisibilityPlanner() {
    }

    public enum TableMode {
        /** 连接级或库/模式级：正常分页查目标库 */
        CATALOG_PAGE,
        /** 仅表级白名单：SQL name IN (...) 下推 */
        NAME_ALLOWLIST,
        /** 无可见表 */
        EMPTY
    }

    /**
     * @param skipCatalog true：不查目标库 catalog，直接用 {@code names}
     * @param names       skipCatalog 时的结果；false 时若非 null 则为与 catalog 的交集白名单
     */
    public record NamePlan(boolean skipCatalog, List<String> names) {
        public static NamePlan empty() {
            return new NamePlan(true, List.of());
        }

        public static NamePlan fromScopes(List<String> names) {
            return new NamePlan(true, List.copyOf(names));
        }

        public static NamePlan catalogAll() {
            return new NamePlan(false, null);
        }

        public static NamePlan catalogIntersect(List<String> allow) {
            return new NamePlan(false, List.copyOf(allow));
        }
    }

    public record TablePlan(TableMode mode, List<String> nameAllowlist) {
        public static TablePlan empty() {
            return new TablePlan(TableMode.EMPTY, List.of());
        }

        public static TablePlan catalog() {
            return new TablePlan(TableMode.CATALOG_PAGE, List.of());
        }

        public static TablePlan allowlist(List<String> names) {
            return new TablePlan(TableMode.NAME_ALLOWLIST, List.copyOf(names));
        }
    }

    public static NamePlan planDatabases(AuthzEvaluateResult authz) {
        ObjectFilter filter = effectiveFilter(authz);
        if (filter == null) {
            return NamePlan.catalogAll();
        }
        if (filter.isUnrestricted()) {
            return NamePlan.catalogAll();
        }
        List<ObjectFilter.Scope> scopes = scopesOf(filter);
        if (scopes.isEmpty()) {
            return NamePlan.empty();
        }
        LinkedHashSet<String> dbs = new LinkedHashSet<>();
        boolean anyBlankDb = false;
        for (ObjectFilter.Scope scope : scopes) {
            if (!StringUtils.hasText(scope.getDatabase())) {
                anyBlankDb = true;
            } else {
                dbs.add(scope.getDatabase().trim());
            }
        }
        if (anyBlankDb) {
            // 无法仅从授权推导库名，需扫 catalog 再 covers
            return NamePlan.catalogAll();
        }
        return NamePlan.fromScopes(new ArrayList<>(dbs));
    }

    public static NamePlan planSchemas(AuthzEvaluateResult authz, String database) {
        ObjectFilter filter = effectiveFilter(authz);
        if (filter == null || filter.isUnrestricted()) {
            return NamePlan.catalogAll();
        }
        List<ObjectFilter.Scope> scopes = scopesOf(filter);
        if (scopes.isEmpty()) {
            return NamePlan.empty();
        }
        boolean dbLevel = false;
        LinkedHashSet<String> schemaNames = new LinkedHashSet<>();
        for (ObjectFilter.Scope scope : scopes) {
            if (!scopeMatchesDatabase(scope, database)) {
                continue;
            }
            String level = normLevel(scope.getLevel());
            if (LEVEL_DATABASE.equals(level)) {
                dbLevel = true;
                break;
            }
            if (LEVEL_SCHEMA.equals(level) || LEVEL_TABLE.equals(level)) {
                if (StringUtils.hasText(scope.getSchema())) {
                    schemaNames.add(scope.getSchema().trim());
                }
            }
        }
        if (dbLevel) {
            return NamePlan.catalogAll();
        }
        if (schemaNames.isEmpty()) {
            return NamePlan.empty();
        }
        return NamePlan.fromScopes(new ArrayList<>(schemaNames));
    }

    public static TablePlan planTables(AuthzEvaluateResult authz, String database, String schema) {
        ObjectFilter filter = effectiveFilter(authz);
        if (filter == null || filter.isUnrestricted()) {
            return TablePlan.catalog();
        }
        List<ObjectFilter.Scope> scopes = scopesOf(filter);
        if (scopes.isEmpty()) {
            return TablePlan.empty();
        }
        LinkedHashSet<String> tableNames = new LinkedHashSet<>();
        boolean wideScope = false;
        for (ObjectFilter.Scope scope : scopes) {
            if (!scopeMatchesDatabase(scope, database)) {
                continue;
            }
            String level = normLevel(scope.getLevel());
            if (LEVEL_DATABASE.equals(level)) {
                wideScope = true;
                break;
            }
            if (LEVEL_SCHEMA.equals(level)) {
                if (eqIgnore(scope.getSchema(), schema)) {
                    wideScope = true;
                    break;
                }
                continue;
            }
            if (LEVEL_TABLE.equals(level)) {
                if (eqIgnore(scope.getSchema(), schema) && StringUtils.hasText(scope.getName())) {
                    tableNames.add(scope.getName().trim());
                }
            }
        }
        if (wideScope) {
            return TablePlan.catalog();
        }
        if (tableNames.isEmpty()) {
            // 兼容仅有旧 filterTables
            List<String> legacy = legacyTableNames(authz, schema);
            if (legacy == null) {
                return TablePlan.catalog();
            }
            if (legacy.isEmpty()) {
                return TablePlan.empty();
            }
            return TablePlan.allowlist(legacy);
        }
        return TablePlan.allowlist(new ArrayList<>(tableNames));
    }

    /** 无 objectFilter 时用旧 filterTables 构造等效过滤器；两者皆无则 null=不限制 */
    private static ObjectFilter effectiveFilter(AuthzEvaluateResult authz) {
        if (authz.getObjectFilter() != null) {
            return authz.getObjectFilter();
        }
        if (authz.getFilterTables() == null) {
            return null;
        }
        List<ObjectFilter.Scope> scopes = new ArrayList<>();
        for (AuthzEvaluateRequest.TableRef ref : authz.getFilterTables()) {
            scopes.add(new ObjectFilter.Scope(
                    LEVEL_TABLE, ref.getDatabase(), ref.getSchema(), ref.getName()));
        }
        return new ObjectFilter(false, scopes);
    }

    private static List<ObjectFilter.Scope> scopesOf(ObjectFilter filter) {
        return filter.getScopes() == null ? List.of() : filter.getScopes();
    }

    /** null = 无旧白名单；empty = 有白名单但本 schema 无表 */
    private static List<String> legacyTableNames(AuthzEvaluateResult authz, String schema) {
        if (authz.getFilterTables() == null) {
            return null;
        }
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (AuthzEvaluateRequest.TableRef ref : authz.getFilterTables()) {
            if (eqIgnore(ref.getSchema(), schema) && StringUtils.hasText(ref.getName())) {
                names.add(ref.getName().trim());
            }
        }
        return new ArrayList<>(names);
    }

    private static boolean scopeMatchesDatabase(ObjectFilter.Scope scope, String database) {
        if (!StringUtils.hasText(scope.getDatabase())) {
            return true;
        }
        return eqIgnore(scope.getDatabase(), database);
    }

    private static String normLevel(String level) {
        return level == null ? "" : level.trim().toUpperCase(Locale.ROOT);
    }

    private static boolean eqIgnore(String a, String b) {
        String x = a == null ? "" : a.trim();
        String y = b == null ? "" : b.trim();
        return x.equalsIgnoreCase(y);
    }

    public static List<String> intersectPreserveOrder(List<String> catalog, List<String> allow) {
        if (allow == null) {
            return catalog;
        }
        if (allow.isEmpty() || catalog == null || catalog.isEmpty()) {
            return List.of();
        }
        Set<String> allowLower = new LinkedHashSet<>();
        for (String a : allow) {
            allowLower.add(a.toLowerCase(Locale.ROOT));
        }
        List<String> out = new ArrayList<>();
        for (String c : catalog) {
            if (c != null && allowLower.contains(c.toLowerCase(Locale.ROOT))) {
                out.add(c);
            }
        }
        return out;
    }
}
