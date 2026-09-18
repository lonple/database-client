package com.lyj.dbc.usercenter.user;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.PageResult;
import com.lyj.dbc.usercenter.security.RequirePermission;
import com.lyj.dbc.usercenter.user.dto.PasswordResetRequest;
import com.lyj.dbc.usercenter.user.dto.UserCreateRequest;
import com.lyj.dbc.usercenter.user.dto.UserQueryRequest;
import com.lyj.dbc.usercenter.user.dto.UserUpdateRequest;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户管理接口。
 */
@Validated
@RestController
@RequestMapping("/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 分页查询用户。
     */
    @GetMapping
    @RequirePermission("usercenter.user.view")
    public ApiResponse<PageResult<UserVO>> page(@Valid UserQueryRequest query) {
        return ApiResponse.ok(userService.page(query));
    }

    /**
     * 新增用户。
     */
    @PostMapping
    @RequirePermission("usercenter.user.operate")
    public ApiResponse<UserVO> create(@Valid @RequestBody UserCreateRequest request) {
        return ApiResponse.ok(userService.create(request));
    }

    /**
     * 编辑用户。
     */
    @PutMapping("/{id}")
    @RequirePermission("usercenter.user.operate")
    public ApiResponse<UserVO> update(@PathVariable @Min(1) Long id,
                                      @Valid @RequestBody UserUpdateRequest request) {
        return ApiResponse.ok(userService.update(id, request));
    }

    /**
     * 逻辑删除用户。
     */
    @DeleteMapping("/{id}")
    @RequirePermission("usercenter.user.operate")
    public ApiResponse<Void> delete(@PathVariable @Min(1) Long id) {
        userService.delete(id);
        return ApiResponse.ok();
    }

    /**
     * 重置密码。
     */
    @PutMapping("/{id}/password")
    @RequirePermission("usercenter.user.operate")
    public ApiResponse<Void> resetPassword(@PathVariable @Min(1) Long id,
                                           @Valid @RequestBody PasswordResetRequest request) {
        userService.resetPassword(id, request);
        return ApiResponse.ok();
    }
}
