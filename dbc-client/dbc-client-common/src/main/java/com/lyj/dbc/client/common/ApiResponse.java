package com.lyj.dbc.client.common;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 跨服务统一响应信封（与各微服务 ApiResponse 字段对齐）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {

    private int code;
    private String message;
    private T data;

    public boolean isSuccess() {
        return code == 0;
    }
}
