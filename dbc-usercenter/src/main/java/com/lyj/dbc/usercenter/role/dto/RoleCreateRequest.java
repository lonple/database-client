package com.lyj.dbc.usercenter.role.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 新建角色请求（仅非内置）。
 */
@Data
public class RoleCreateRequest {

    /** 角色编码 */
    @NotBlank(message = "角色编码不能为空")
    @Size(max = 64, message = "角色编码长度不能超过64")
    @Pattern(regexp = "^[A-Z][A-Z0-9_]*$", message = "角色编码须大写字母开头，仅含大写字母数字下划线")
    private String code;

    /** 角色名称 */
    @NotBlank(message = "角色名称不能为空")
    @Size(max = 64, message = "角色名称长度不能超过64")
    private String name;

    /** 角色说明，可选 */
    @Size(max = 255, message = "说明长度不能超过255")
    private String description;

    /**
     * 数据范围。
     * ALL / DEPT_AND_CHILDREN / DEPT_ONLY / CUSTOM
     */
    @NotBlank(message = "数据范围不能为空")
    @Pattern(regexp = "^(ALL|DEPT_AND_CHILDREN|DEPT_ONLY|CUSTOM)$", message = "数据范围取值非法")
    private String dataScope;

    /** CUSTOM 时勾选的部门ID列表 */
    private List<Long> deptIds;
}
