package com.lyj.dbc.knowledge.common.api;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotWritableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;

/**
 * 统一异常处理。强制 JSON Content-Type，避免 SSE / Accept 协商导致无法写出 ApiResponse。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public ResponseEntity<ApiResponse<Void>> handleBiz(BizException e) {
        log.warn("业务异常 code={}", e.getCode(), e);
        return json(ApiResponse.fail(e.getCode(), e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(err -> err.getField() + ": " + err.getDefaultMessage())
                .orElse("validation failed");
        log.warn("参数校验失败: {}", msg, e);
        return json(ApiResponse.fail(400, msg));
    }

    @ExceptionHandler({
            AsyncRequestNotUsableException.class,
            HttpMessageNotWritableException.class
    })
    public ResponseEntity<Void> handleUnusableResponse(Exception e, HttpServletRequest request) {
        log.debug("响应不可写 path={} msg={}", request.getRequestURI(), e.getMessage());
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleOther(Exception e, HttpServletRequest request) {
        log.error("未捕获异常 path={}", request.getRequestURI(), e);
        String msg = e.getMessage() == null ? "internal error" : e.getMessage();
        return json(ApiResponse.fail(500, msg));
    }

    private static ResponseEntity<ApiResponse<Void>> json(ApiResponse<Void> body) {
        return ResponseEntity.status(HttpStatus.OK)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body);
    }
}
