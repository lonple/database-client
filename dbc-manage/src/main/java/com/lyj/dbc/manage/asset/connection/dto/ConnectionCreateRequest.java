package com.lyj.dbc.manage.asset.connection.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ConnectionCreateRequest {

    @NotBlank(message = "连接名称不能为空")
    @Size(max = 128)
    private String name;

    /** 公司域必填；个人域忽略 */
    private Long deptId;

    @NotNull(message = "实例不能为空")
    private Long instanceId;

    @NotBlank(message = "用户名不能为空")
    @Size(max = 128)
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(max = 512)
    private String password;

    @Size(max = 128)
    private String initialDatabase;

    @Min(0)
    @Max(1)
    private Integer status = 1;
}
