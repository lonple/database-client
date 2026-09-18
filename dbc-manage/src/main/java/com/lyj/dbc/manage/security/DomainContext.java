package com.lyj.dbc.manage.security;

/**
 * 当前请求的业务域（公司 / 个人），由 {@link DomainContextFilter} 写入。
 */
public final class DomainContext {

    private static final ThreadLocal<String> HOLDER = new ThreadLocal<>();

    private DomainContext() {
    }

    public static void set(String domain) {
        HOLDER.set(DomainCodes.normalize(domain));
    }

    public static String get() {
        String v = HOLDER.get();
        return v == null ? DomainCodes.COMPANY : v;
    }

    public static boolean isPersonal() {
        return DomainCodes.isPersonal(get());
    }

    public static boolean isCompany() {
        return !isPersonal();
    }

    public static void clear() {
        HOLDER.remove();
    }
}
