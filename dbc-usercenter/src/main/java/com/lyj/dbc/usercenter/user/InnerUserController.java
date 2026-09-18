package com.lyj.dbc.usercenter.user;

import com.lyj.dbc.usercenter.common.ApiResponse;
import com.lyj.dbc.usercenter.common.PageResult;
import com.lyj.dbc.usercenter.user.dto.UserQueryRequest;
import com.lyj.dbc.usercenter.user.vo.UserVO;
import jakarta.validation.Valid;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户 inner API：供其它微服务经 mTLS 调用，不做终端用户功能权限判定。
 * <p>
 * 用于工作空间选人等场景；调用方须自行做业务侧鉴权（如 auth.workspace.*）。
 */
@Validated
@RestController
@RequestMapping("/inner/users")
public class InnerUserController {

    private final UserService userService;

    public InnerUserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public ApiResponse<PageResult<UserVO>> page(@Valid UserQueryRequest query) {
        return ApiResponse.ok(userService.page(query));
    }
}
