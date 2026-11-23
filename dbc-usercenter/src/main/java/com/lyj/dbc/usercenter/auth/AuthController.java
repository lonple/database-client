package com.lyj.dbc.usercenter.auth;

import com.lyj.dbc.usercenter.auth.dto.LoginRequest;
import com.lyj.dbc.usercenter.auth.dto.LoginResponse;
import com.lyj.dbc.usercenter.auth.vo.DataScopeVO;
import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
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
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request,
                                            HttpServletResponse response) {
        return ApiResponse.ok(authService.login(request, response));
    }

    /**
     * 刷新 access（凭 refresh Cookie + CSRF）。
     */
    @PostMapping("/refresh")
    public ApiResponse<LoginResponse> refresh(HttpServletRequest request, HttpServletResponse response) {
        return ApiResponse.ok(authService.refresh(request, response));
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
     * 退出登录。
     */
    @PostMapping("/logout")
    public ApiResponse<Void> logout(HttpServletRequest request, HttpServletResponse response) {
        authService.logout(request, response);
        return ApiResponse.ok();
    }
}
