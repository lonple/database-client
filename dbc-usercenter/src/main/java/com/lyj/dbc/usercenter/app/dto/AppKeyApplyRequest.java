package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 为实例申请密钥对（私钥留在用户中心）。
 */
@Data
public class AppKeyApplyRequest {

    /** 实例 ID，同一应用下区分多实例 */
    @NotBlank
    @Size(max = 128)
    private String instanceId;
}
