package com.lyj.dbc.manage.security;

/**
 * 公司域 / 个人域编码（请求头 X-Dbc-Domain、空间类型、资产归属共用）。
 */
public final class DomainCodes {

    public static final String COMPANY = "COMPANY";
    public static final String PERSONAL = "PERSONAL";
    public static final String HEADER = "X-Dbc-Domain";

    private DomainCodes() {
    }

    public static boolean isPersonal(String code) {
        return PERSONAL.equalsIgnoreCase(code == null ? "" : code.trim());
    }

    public static boolean isCompany(String code) {
        return !isPersonal(code);
    }

    /**
     * 非法值回落为 COMPANY。
     */
    public static String normalize(String raw) {
        if (raw == null || raw.isBlank()) {
            return COMPANY;
        }
        String v = raw.trim().toUpperCase();
        if (PERSONAL.equals(v)) {
            return PERSONAL;
        }
        return COMPANY;
    }
}
