package com.lyj.dbc.usercenter.user.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 新增用户请求参数。
 */
@Data
public class UserCreateRequest {

    /** 登录账号 */
    @NotBlank(message = "账号不能为空")
    @Size(max = 64, message = "账号长度不能超过64")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "账号仅允许字母数字下划线")
    private String username;

    /** 初始密码 */
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 64, message = "密码长度需在6-64之间")
    private String password;

    /** 角色ID列表，至少一个 */
    @NotEmpty(message = "至少绑定一个角色")
    private List<@NotNull @Min(1) Long> roleIds;

    /** 归属部门ID，可选 */
    @Min(value = 1, message = "部门ID非法")
    private Long deptId;

    /** 手机号，可选 */
    @Size(max = 20, message = "手机号长度不能超过20")
    @Pattern(regexp = "^$|^1\\d{10}$", message = "手机号格式不正确")
    private String mobile;

    /** 用户描述，可选 */
    @Size(max = 512, message = "描述长度不能超过512")
    private String description;

    /**
     * 状态。
     * 1：启用；0：禁用
     */
    @NotNull(message = "状态不能为空")
    @Min(value = 0, message = "状态取值非法")
    @Max(value = 1, message = "状态取值非法")
    private Integer status = 1;
}
