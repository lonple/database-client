package com.lyj.dbc.usercenter.user.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 用户分页查询请求参数。
 */
@Data
public class UserQueryRequest {

    /** 页码，从1开始 */
    @Min(value = 1, message = "页码最小为1")
    private long page = 1;

    /** 每页条数 */
    @Min(value = 1, message = "每页条数最小为1")
    @Max(value = 100, message = "每页条数不能超过100")
    private long size = 10;

    /** 账号模糊查询，可选 */
    @Size(max = 64, message = "账号长度不能超过64")
    private String username;
}
