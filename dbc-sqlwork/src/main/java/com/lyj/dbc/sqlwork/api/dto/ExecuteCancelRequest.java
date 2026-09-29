package com.lyj.dbc.sqlwork.api.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 取消进行中的 SQL 执行。
 */
@Data
public class ExecuteCancelRequest {

    @NotBlank(message = "cancelToken 不能为空")
    private String cancelToken;
}
