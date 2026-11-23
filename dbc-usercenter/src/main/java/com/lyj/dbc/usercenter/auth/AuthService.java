package com.lyj.dbc.usercenter.auth;

import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.auth.dto.LoginRequest;
import com.lyj.dbc.usercenter.auth.dto.LoginResponse;
import com.lyj.dbc.usercenter.auth.vo.DataScopeVO;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.permission.PermissionService;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.security.AuthCookieService;
import com.lyj.dbc.usercenter.security.JwtService;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.user.UserService;
import com.lyj.dbc.usercenter.user.entity.UserEntity;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 认证业务服务。
 */
@Service
public class AuthService {

    private final UserService userService;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthCookieService authCookieService;
    private final DataScopeService dataScopeService;
    private final PermissionService permissionService;

    public AuthService(UserService userService, PasswordEncoder passwordEncoder,
                       JwtService jwtService, AuthCookieService authCookieService,
                       DataScopeService dataScopeService, PermissionService permissionService) {
        this.userService = userService;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.authCookieService = authCookieService;
        this.dataScopeService = dataScopeService;
        this.permissionService = permissionService;
    }

    /**
     * 账号密码登录：签发 access（JSON）+ refresh/csrf（Cookie）。
     */
    @AuditLog(module = "usercenter", action = AuditAction.LOGIN, resourceType = "session", resourceId = "#request.username")
    public LoginResponse login(LoginRequest request, HttpServletResponse response) {
        UserEntity user = userService.loadEntityByUsername(request.getUsername().trim());
        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw BizException.unauthorized("用户名或密码错误");
        }
        if (user.getStatus() == null || user.getStatus() != 1) {
            throw BizException.unauthorized("账号已禁用");
        }
        List<RoleEntity> roles = userService.listRolesOfUser(user.getId());
        if (roles.isEmpty()) {
            throw BizException.unauthorized("用户未绑定角色");
        }
        List<String> roleCodes = roles.stream().map(RoleEntity::getCode).toList();
        LoginUser loginUser = new LoginUser(user.getId(), user.getUsername(), roleCodes);
        return issueSession(loginUser, buildCurrentUser(user.getId()), response);
    }

    /**
     * 用 refresh Cookie 换新 access（轮换 refresh/csrf）。
     */
    public LoginResponse refresh(HttpServletRequest request, HttpServletResponse response) {
        String refreshToken = authCookieService.readRefresh(request)
                .orElseThrow(() -> BizException.unauthorized("未登录或令牌无效"));
        Claims claims;
        try {
            claims = jwtService.parseRefreshClaims(refreshToken);
        } catch (Exception e) {
            authCookieService.clearSessionCookies(response);
            throw BizException.unauthorized("未登录或令牌无效");
        }
        jwtService.denyClaims(claims);
        LoginUser loginUser = jwtService.toUser(claims);
        UserEntity user = userService.loadEntityByUsername(loginUser.getUsername());
        if (user == null || user.getStatus() == null || user.getStatus() != 1) {
            authCookieService.clearSessionCookies(response);
            throw BizException.unauthorized("账号已禁用");
        }
        return issueSession(loginUser, null, response);
    }

    /**
     * 退出：吊销 access/refresh jti，清除 Cookie。
     */
    @AuditLog(module = "usercenter", action = AuditAction.LOGOUT, resourceType = "session")
    public void logout(HttpServletRequest request, HttpServletResponse response) {
        String auth = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (auth != null && auth.startsWith("Bearer ")) {
            jwtService.denyToken(auth.substring(7).trim());
        }
        authCookieService.readRefresh(request).ifPresent(jwtService::denyToken);
        authCookieService.clearSessionCookies(response);
    }

    /**
     * 当前登录用户信息（含权限码）。
     */
    public UserVO me() {
        LoginUser loginUser = SecurityUtils.requireUser();
        return buildCurrentUser(loginUser.getUserId());
    }

    /**
     * 当前用户数据范围。
     */
    public DataScopeVO dataScope() {
        LoginUser loginUser = SecurityUtils.requireUser();
        return dataScopeService.resolve(loginUser.getUserId());
    }

    private LoginResponse issueSession(LoginUser loginUser, UserVO user, HttpServletResponse response) {
        JwtService.IssuedToken access = jwtService.createAccessToken(loginUser);
        JwtService.IssuedToken refresh = jwtService.createRefreshToken(loginUser);
        String csrf = authCookieService.newCsrfToken();
        authCookieService.writeSessionCookies(response, refresh.token(), csrf, jwtService.refreshTtl());
        return new LoginResponse(access.token(), jwtService.accessExpireSeconds(), user);
    }

    private UserVO buildCurrentUser(Long userId) {
        UserVO view = userService.getById(userId);
        view.setPermissions(permissionService.listPermissionCodesByUser(userId));
        return view;
    }
}
