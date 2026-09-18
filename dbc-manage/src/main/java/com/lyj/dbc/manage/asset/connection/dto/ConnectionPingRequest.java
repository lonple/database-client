package com.lyj.dbc.manage.asset.connection.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 创建/编辑表单探活请求（可尚未落库）。
 */
@Data
public class ConnectionPingRequest {

    /** 编辑时传入：密码留空则使用已存密文 */
    private Long connectionId;

    @NotNull(message = "实例不能为空")
    private Long instanceId;

    @NotBlank(message = "用户名不能为空")
    @Size(max = 128)
    private String username;

    /** 新建必填；编辑可空表示沿用原密码 */
    @Size(max = 512)
    private String password;

    @Size(max = 128)
    private String initialDatabase;
}
