package com.lyj.dbc.audit.common;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * 业务异常，携带 HTTP 状态。
 */
@Getter
public class BizException extends RuntimeException {

    private final HttpStatus status;

    public BizException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public static BizException badRequest(String message) {
        return new BizException(HttpStatus.BAD_REQUEST, message);
    }

    public static BizException unauthorized(String message) {
        return new BizException(HttpStatus.UNAUTHORIZED, message);
    }

    public static BizException notFound(String message) {
        return new BizException(HttpStatus.NOT_FOUND, message);
    }

    public static BizException forbidden(String message) {
        return new BizException(HttpStatus.FORBIDDEN, message);
    }

    public static BizException serviceUnavailable(String message) {
        return new BizException(HttpStatus.SERVICE_UNAVAILABLE, message);
    }
}
