package com.lyj.dbc.client.common;

/**
 * 调用对端 inner 接口失败。
 */
public class InnerClientException extends RuntimeException {

    private final int code;

    public InnerClientException(String message) {
        this(message, -1, null);
    }

    public InnerClientException(String message, Throwable cause) {
        this(message, -1, cause);
    }

    public InnerClientException(String message, int code) {
        this(message, code, null);
    }

    public InnerClientException(String message, int code, Throwable cause) {
        super(message, cause);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
