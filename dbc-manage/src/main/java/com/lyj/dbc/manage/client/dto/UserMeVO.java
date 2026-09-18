package com.lyj.dbc.manage.client.dto;

import lombok.Data;

import java.util.List;

/**
 * 对应用户中心 /auth/me 中权限相关字段（其余字段可忽略）。
 */
@Data
public class UserMeVO {

    private Long id;
    private String username;
    private Long deptId;
    private List<String> permissions;
}
