package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 吊销公钥请求。
 */
@Data
public class AppKeyRevokeRequest {

    /** 密钥 ID */
    @NotBlank
    @Size(max = 128)
    private String kid;
}
