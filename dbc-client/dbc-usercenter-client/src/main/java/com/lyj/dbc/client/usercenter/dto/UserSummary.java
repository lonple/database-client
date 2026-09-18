package com.lyj.dbc.client.usercenter.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户摘要（inner / 选人门面；不含密码）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserSummary {

    private Long id;
    private String username;
    private Integer status;
    private Long deptId;
    private String deptName;
}
