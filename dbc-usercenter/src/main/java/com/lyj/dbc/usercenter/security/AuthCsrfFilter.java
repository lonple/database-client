package com.lyj.dbc.usercenter.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.usercenter.common.ApiResponse;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * 仅校验 /auth/refresh、/auth/logout 的 Double-Submit CSRF。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class AuthCsrfFilter extends OncePerRequestFilter {

    private final AuthCookieService authCookieService;
    private final ObjectMapper objectMapper;

    public AuthCsrfFilter(AuthCookieService authCookieService, ObjectMapper objectMapper) {
        this.authCookieService = authCookieService;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        if (!"POST".equalsIgnoreCase(request.getMethod())) {
            return true;
        }
        return !(path.endsWith("/auth/refresh") || path.endsWith("/auth/logout"));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String header = request.getHeader(AuthCookieService.CSRF_HEADER);
        String cookie = authCookieService.readCsrf(request).orElse(null);
        if (header == null || cookie == null || !constantTimeEquals(header, cookie)) {
            writeForbidden(response, "CSRF 校验失败");
            return;
        }
        filterChain.doFilter(request, response);
    }

    private static boolean constantTimeEquals(String a, String b) {
        byte[] x = a.getBytes(StandardCharsets.UTF_8);
        byte[] y = b.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(x, y);
    }

    private void writeForbidden(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(403, message));
    }
}
