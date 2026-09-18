package com.lyj.dbc.usercenter.auth;

import com.lyj.dbc.usercenter.auth.dto.LoginRequest;
import com.lyj.dbc.usercenter.auth.dto.LoginResponse;
import com.lyj.dbc.usercenter.auth.vo.DataScopeVO;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口。
 */
@RestController
@RequestMapping("/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * 登录。
     */
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.ok(authService.login(request));
    }

    /**
     * 当前用户。
     */
    @GetMapping("/me")
    public ApiResponse<UserVO> me() {
        return ApiResponse.ok(authService.me());
    }

    /**
     * 当前用户数据范围（供资产等服务使用）。
     */
    @GetMapping("/data-scope")
    public ApiResponse<DataScopeVO> dataScope() {
        return ApiResponse.ok(authService.dataScope());
    }

    /**
     * 退出登录（记审计；客户端清 Token）。
     */
    @PostMapping("/logout")
    public ApiResponse<Void> logout() {
        authService.logout();
        return ApiResponse.ok();
    }
}
