package com.lyj.dbc.usercenter.auth;

import com.lyj.dbc.client.audit.AuditAction;
import com.lyj.dbc.client.audit.AuditLog;
import com.lyj.dbc.usercenter.auth.dto.LoginRequest;
import com.lyj.dbc.usercenter.auth.dto.LoginResponse;
import com.lyj.dbc.usercenter.auth.vo.DataScopeVO;
import com.lyj.dbc.usercenter.common.BizException;
import com.lyj.dbc.usercenter.permission.PermissionService;
import com.lyj.dbc.usercenter.role.entity.RoleEntity;
import com.lyj.dbc.usercenter.security.JwtService;
import com.lyj.dbc.usercenter.security.LoginUser;
import com.lyj.dbc.usercenter.security.SecurityUtils;
import com.lyj.dbc.usercenter.user.UserService;
import com.lyj.dbc.usercenter.user.entity.UserEntity;
import com.lyj.dbc.usercenter.user.vo.UserVO;
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
    private final DataScopeService dataScopeService;
    private final PermissionService permissionService;

    public AuthService(UserService userService, PasswordEncoder passwordEncoder,
                       JwtService jwtService, DataScopeService dataScopeService,
                       PermissionService permissionService) {
        this.userService = userService;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.dataScopeService = dataScopeService;
        this.permissionService = permissionService;
    }

    /**
     * 账号密码登录。
     */
    @AuditLog(module = "usercenter", action = AuditAction.LOGIN, resourceType = "session", resourceId = "#request.username")
    public LoginResponse login(LoginRequest request) {
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
        String token = jwtService.createToken(loginUser);
        return new LoginResponse(token, jwtService.expireSeconds(), buildCurrentUser(user.getId()));
    }

    /**
     * 退出登录（客户端清 Token；服务端记审计）。
     */
    @AuditLog(module = "usercenter", action = AuditAction.LOGOUT, resourceType = "session")
    public void logout() {
        SecurityUtils.requireUser();
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

    private UserVO buildCurrentUser(Long userId) {
        UserVO view = userService.getById(userId);
        view.setPermissions(permissionService.listPermissionCodesByUser(userId));
        return view;
    }
}
