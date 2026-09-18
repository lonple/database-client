package com.lyj.dbc.usercenter.permission.vo;

import lombok.Builder;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 按业务大模块分组的权限。
 */
@Data
@Builder
public class PermissionModuleVO {

    /** 业务大模块编码 */
    private String moduleCode;

    /** 业务大模块名称 */
    private String moduleName;

    /** 该模块下权限列表 */
    @Builder.Default
    private List<PermissionVO> permissions = new ArrayList<>();
}
