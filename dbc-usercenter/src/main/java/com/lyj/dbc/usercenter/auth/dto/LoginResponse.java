package com.lyj.dbc.usercenter.auth.dto;

import com.lyj.dbc.usercenter.user.vo.UserVO;
import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 登录成功响应。
 */
@Data
@AllArgsConstructor
public class LoginResponse {

    /** JWT 访问令牌 */
    private String token;

    /** 令牌有效期（秒） */
    private long expiresIn;

    /** 当前用户信息 */
    private UserVO user;
}
