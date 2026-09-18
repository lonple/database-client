package com.lyj.dbc.usercenter.mtls;

/**
 * 当前请求经 mTLS 解析出的应用 clientId。
 */
public final class MtlsClientContext {

    private static final ThreadLocal<String> CLIENT_ID = new ThreadLocal<>();

    private MtlsClientContext() {
    }

    public static void setClientId(String clientId) {
        CLIENT_ID.set(clientId);
    }

    public static String getClientId() {
        return CLIENT_ID.get();
    }

    public static void clear() {
        CLIENT_ID.remove();
    }
}
