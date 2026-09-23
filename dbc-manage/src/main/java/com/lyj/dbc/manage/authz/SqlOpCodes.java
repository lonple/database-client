package com.lyj.dbc.manage.authz;

import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * SQL 操作权限码。
 * <p>
 * {@link #ANY} 表示<strong>任意 SQL</strong>（含解析为 OTHER 等未在 DML/DDL 枚举中的语句），
 * 不等于「勾选全部已列举的 DML+DDL」。
 */
public final class SqlOpCodes {

    private SqlOpCodes() {
    }

    /** 任意 SQL（哨兵）；ops_json 含此值时匹配任意 sqlOp */
    public static final String ANY = "ANY";

    public static final List<String> DML_OPS = List.of("SELECT", "INSERT", "UPDATE", "DELETE");
    public static final List<String> DDL_OPS = List.of("CREATE", "ALTER", "DROP", "TRUNCATE", "COMMENT", "INDEX");
    /** 产品枚举的具名操作（不含 ANY） */
    public static final List<String> NAMED_OPS;

    static {
        List<String> named = new ArrayList<>(DML_OPS.size() + DDL_OPS.size());
        named.addAll(DML_OPS);
        named.addAll(DDL_OPS);
        NAMED_OPS = List.copyOf(named);
    }

    private static final Set<String> NAMED_SET = Set.copyOf(NAMED_OPS);

    public static boolean isAny(String op) {
        return StringUtils.hasText(op) && ANY.equalsIgnoreCase(op.trim());
    }

    public static boolean includesAny(Collection<String> ops) {
        if (ops == null || ops.isEmpty()) {
            return false;
        }
        for (String op : ops) {
            if (isAny(op)) {
                return true;
            }
        }
        return false;
    }

    /** 授权/策略是否覆盖给定 sqlOp（ANY 覆盖一切）。 */
    public static boolean covers(Collection<String> grantedOps, String sqlOp) {
        if (grantedOps == null || grantedOps.isEmpty() || !StringUtils.hasText(sqlOp)) {
            return false;
        }
        if (includesAny(grantedOps)) {
            return true;
        }
        String want = sqlOp.trim().toUpperCase(Locale.ROOT);
        for (String op : grantedOps) {
            if (StringUtils.hasText(op) && want.equalsIgnoreCase(op.trim())) {
                return true;
            }
        }
        return false;
    }

    /**
     * 规范化写入用 ops：去空、大写、去重；若含 ANY 则折叠为仅 {@code ["ANY"]}。
     */
    public static List<String> normalize(Collection<String> ops) {
        if (ops == null || ops.isEmpty()) {
            return List.of();
        }
        LinkedHashSet<String> set = new LinkedHashSet<>();
        boolean any = false;
        for (String raw : ops) {
            if (!StringUtils.hasText(raw)) {
                continue;
            }
            String op = raw.trim().toUpperCase(Locale.ROOT);
            if (ANY.equals(op)) {
                any = true;
                break;
            }
            if (!NAMED_SET.contains(op)) {
                // 允许历史/扩展码原样保留；非法码由调用方再校验
                set.add(op);
            } else {
                set.add(op);
            }
        }
        if (any) {
            return List.of(ANY);
        }
        return List.copyOf(set);
    }

    /** 是否允许作为资产/成员/策略写入的操作码 */
    public static boolean isAllowedWriteOp(String op) {
        if (!StringUtils.hasText(op)) {
            return false;
        }
        String u = op.trim().toUpperCase(Locale.ROOT);
        return ANY.equals(u) || NAMED_SET.contains(u);
    }

    /**
     * grantOps ⊆ allowedOps；allowed 含 ANY 时任意 grant 均可；grant 含 ANY 时 allowed 也须含 ANY。
     */
    public static boolean isSubset(Collection<String> grantOps, Collection<String> allowedOps) {
        if (grantOps == null || grantOps.isEmpty()) {
            return false;
        }
        if (includesAny(allowedOps)) {
            return true;
        }
        if (includesAny(grantOps)) {
            return false;
        }
        Set<String> allowed = new LinkedHashSet<>();
        if (allowedOps != null) {
            for (String o : allowedOps) {
                if (StringUtils.hasText(o)) {
                    allowed.add(o.trim().toUpperCase(Locale.ROOT));
                }
            }
        }
        for (String g : grantOps) {
            if (!StringUtils.hasText(g)) {
                continue;
            }
            if (!allowed.contains(g.trim().toUpperCase(Locale.ROOT))) {
                return false;
            }
        }
        return true;
    }
}
