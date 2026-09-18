package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 创建应用请求。
 */
@Data
public class AppCreateRequest {

    /** 应用 clientId */
    @NotBlank
    @Size(max = 64)
    private String clientId;

    /** 应用名称 */
    @NotBlank
    @Size(max = 128)
    private String appName;
}
