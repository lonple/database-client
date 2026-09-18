package com.lyj.dbc.manage.security;

import com.lyj.dbc.manage.client.UserCenterClient;
import com.lyj.dbc.manage.client.dto.DataScopeVO;
import com.lyj.dbc.manage.client.dto.UserMeVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
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
 * JWT 鉴权后按请求拉取一次 usercenter 权限与数据范围，写入请求属性。
 */
@Component
@Order
public class UserContextFilter extends OncePerRequestFilter {

    public static final String ATTR_PERMISSIONS = "dbc.manage.permissions";
    public static final String ATTR_DATA_SCOPE = "dbc.manage.dataScope";
    public static final String ATTR_BEARER = "dbc.manage.bearer";

    private final UserCenterClient userCenterClient;
    private final ObjectMapper objectMapper;

    public UserContextFilter(UserCenterClient userCenterClient, ObjectMapper objectMapper) {
        this.userCenterClient = userCenterClient;
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof LoginUser && auth.getCredentials() instanceof String token) {
            try {
                UserMeVO me = userCenterClient.fetchMe(token);
                DataScopeVO scope = userCenterClient.fetchDataScope(token);
                List<String> permissions = me.getPermissions() == null ? Collections.emptyList() : me.getPermissions();
                request.setAttribute(ATTR_PERMISSIONS, permissions);
                request.setAttribute(ATTR_DATA_SCOPE, scope);
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
