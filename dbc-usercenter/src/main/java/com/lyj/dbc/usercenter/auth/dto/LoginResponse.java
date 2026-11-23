package com.lyj.dbc.usercenter.auth.dto;

import com.lyj.dbc.usercenter.user.vo.UserVO;
import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 登录 / 刷新成功响应。accessToken 仅供前端写入内存，不得持久化。
 */
@Data
@AllArgsConstructor
public class LoginResponse {

    /** 短命 access JWT */
    private String accessToken;

    /** access 有效期（秒） */
    private long expiresIn;

    /** 当前用户信息（登录时返回；刷新时可为空） */
    private UserVO user;
}
