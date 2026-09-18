package com.lyj.dbc.usercenter.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 登录请求参数。
 */
@Data
public class LoginRequest {

    /** 登录账号 */
    @NotBlank(message = "账号不能为空")
    @Size(max = 64, message = "账号长度不能超过64")
    private String username;

    /** 登录密码 */
    @NotBlank(message = "密码不能为空")
    @Size(min = 1, max = 64, message = "密码长度不能超过64")
    private String password;
}
