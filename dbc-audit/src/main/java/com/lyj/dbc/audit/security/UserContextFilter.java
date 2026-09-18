package com.lyj.dbc.audit.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lyj.dbc.audit.client.UserCenterHttpClient;
import com.lyj.dbc.audit.client.dto.UserMeVO;
import com.lyj.dbc.audit.common.ApiResponse;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

/**
 * JWT 鉴权后按请求拉取一次 usercenter /auth/me 权限，写入请求属性。
 */
@Component
public class UserContextFilter extends OncePerRequestFilter {

    public static final String ATTR_PERMISSIONS = "dbc.audit.permissions";
    public static final String ATTR_BEARER = "dbc.audit.bearer";

    private final UserCenterHttpClient userCenterHttpClient;
    private final ObjectMapper objectMapper;

    public UserContextFilter(UserCenterHttpClient userCenterHttpClient, ObjectMapper objectMapper) {
        this.userCenterHttpClient = userCenterHttpClient;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        if (uri == null) {
            return true;
        }
        return uri.startsWith("/inner/") || uri.startsWith("/actuator");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof LoginUser && auth.getCredentials() instanceof String token) {
            try {
                UserMeVO me = userCenterHttpClient.fetchMe(token);
                List<String> permissions = me.getPermissions() == null ? Collections.emptyList() : me.getPermissions();
                request.setAttribute(ATTR_PERMISSIONS, permissions);
                request.setAttribute(ATTR_BEARER, token);
            } catch (Exception ex) {
                writeUnauthorized(response, "拉取用户权限失败: " + ex.getMessage());
                return;
            }
        }
        filterChain.doFilter(request, response);
    }

    private void writeUnauthorized(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(401, message));
    }
}
