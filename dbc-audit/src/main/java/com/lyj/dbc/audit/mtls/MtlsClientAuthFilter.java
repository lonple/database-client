package com.lyj.dbc.audit.mtls;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.audit.common.ApiResponse;
import com.lyj.dbc.audit.common.BizException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.security.auth.x500.X500Principal;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.cert.X509Certificate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * /inner/** 须走 mTLS 端口并提供客户端证书；解析 CN 为 clientId。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 5)
public class MtlsClientAuthFilter extends OncePerRequestFilter {

    private static final Pattern CN = Pattern.compile("CN=([^,]+)", Pattern.CASE_INSENSITIVE);

    private final ObjectMapper objectMapper;

    public MtlsClientAuthFilter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        if (uri == null) {
            return true;
        }
        return !uri.startsWith("/inner/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        try {
            boolean secure = request.isSecure();
            X509Certificate[] certs = (X509Certificate[]) request.getAttribute("jakarta.servlet.request.X509Certificate");
            if (!secure || certs == null || certs.length == 0) {
                certs = (X509Certificate[]) request.getAttribute("javax.servlet.request.X509Certificate");
            }
            if (!secure || certs == null || certs.length == 0) {
                writeForbidden(response, "该接口须通过 mTLS 端口访问并提供客户端证书");
                return;
            }
            String clientId = extractCn(certs[0].getSubjectX500Principal());
            if (clientId == null || clientId.isBlank()) {
                writeForbidden(response, "客户端证书缺少 CN");
                return;
            }
            MtlsClientContext.setClientId(clientId.trim());
            filterChain.doFilter(request, response);
        } catch (BizException ex) {
            writeForbidden(response, ex.getMessage());
        } finally {
            MtlsClientContext.clear();
        }
    }

    static String extractCn(X500Principal principal) {
        if (principal == null) {
            return null;
        }
        Matcher m = CN.matcher(principal.getName());
        if (m.find()) {
            return m.group(1).trim();
        }
        return null;
    }

    private void writeForbidden(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(403, message));
    }
}
