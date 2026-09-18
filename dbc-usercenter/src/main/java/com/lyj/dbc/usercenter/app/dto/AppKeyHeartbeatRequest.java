package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 公钥心跳请求（按实例）。
 */
@Data
public class AppKeyHeartbeatRequest {

    /** 实例 ID */
    @NotBlank
    @Size(max = 128)
    private String instanceId;
}
