package com.lyj.dbc.usercenter.svcsign;

import com.lyj.dbc.usercenter.app.entity.AppKeyEntity;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.config.SvcSignProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.PublicKey;

/**
 * 对 /inner/** 请求验签（密钥注册类接口除外）。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class InnerRequestSignFilter extends OncePerRequestFilter {

    private final PublicKeyCache publicKeyCache;
    private final RedisNonceService nonceService;
    private final SvcSignProperties properties;
    private final ObjectMapper objectMapper;

    public InnerRequestSignFilter(PublicKeyCache publicKeyCache, RedisNonceService nonceService,
                                  SvcSignProperties properties, ObjectMapper objectMapper) {
        this.publicKeyCache = publicKeyCache;
        this.nonceService = nonceService;
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        // 网关 Strip 后为 /inner/...；本地直连同样
        if (!path.contains("/inner/")) {
            return true;
        }
        return path.contains("/inner/apps/keys/")
                || path.contains("/inner/permissions/")
                || path.contains("/inner/depts/")
                || path.contains("/inner/users");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        ContentCachingRequestWrapper wrapped = request instanceof ContentCachingRequestWrapper
                ? (ContentCachingRequestWrapper) request
                : new ContentCachingRequestWrapper(request);
        try {
            verify(wrapped);
            filterChain.doFilter(wrapped, response);
        } catch (BizException ex) {
            writeUnauthorized(response, ex.getMessage());
        }
    }

    private void verify(ContentCachingRequestWrapper request) throws IOException {
        String clientId = request.getHeader(OutboundRequestSigner.H_CLIENT_ID);
        String kid = request.getHeader(OutboundRequestSigner.H_KEY_ID);
        String ts = request.getHeader(OutboundRequestSigner.H_TIMESTAMP);
        String nonce = request.getHeader(OutboundRequestSigner.H_NONCE);
        String signature = request.getHeader(OutboundRequestSigner.H_SIGNATURE);
        if (isBlank(clientId) || isBlank(kid) || isBlank(ts) || isBlank(nonce) || isBlank(signature)) {
            throw BizException.unauthorized("缺少服务签名头");
        }
        long timestamp;
        try {
            timestamp = Long.parseLong(ts);
        } catch (NumberFormatException e) {
            throw BizException.unauthorized("时间戳无效");
        }
        long now = System.currentTimeMillis() / 1000;
        if (Math.abs(now - timestamp) > properties.getTimestampSkewSeconds()) {
            throw BizException.unauthorized("请求时间戳超出允许窗口");
        }
        // 先读 body 到缓存
        byte[] body = request.getInputStream().readAllBytes();
        String path = request.getRequestURI();
        // 若经 context-path 等，保持 servlet path
        String servletPath = request.getServletPath();
        if (servletPath != null && !servletPath.isBlank()) {
            path = servletPath;
        }
        String stringToSign = SignCanonical.build(
                request.getMethod(), path, request.getQueryString(), ts, nonce, body);
        PublicKey publicKey = publicKeyCache.get(clientId, kid);
        if (publicKey == null) {
            throw BizException.unauthorized("未知或已失活的签名密钥");
        }
        if (!EcdsaSignSupport.verify(publicKey, stringToSign, signature)) {
            throw BizException.unauthorized("服务签名校验失败");
        }
        nonceService.consumeOrReject(properties.getClientId(), clientId, nonce);
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    private void writeUnauthorized(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(401, message));
    }
}
