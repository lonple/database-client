package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 按实例轮换密钥。
 */
@Data
public class AppKeyRotateRequest {

    /** 实例 ID */
    @NotBlank
    @Size(max = 128)
    private String instanceId;
}
