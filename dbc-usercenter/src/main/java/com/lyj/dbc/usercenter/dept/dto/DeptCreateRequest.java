package com.lyj.dbc.usercenter.dept.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 新增部门请求。
 */
@Data
public class DeptCreateRequest {

    /** 部门名称 */
    @NotBlank(message = "部门名称不能为空")
    @Size(max = 64, message = "部门名称长度不能超过64")
    private String name;

    /** 部门描述，可选 */
    @Size(max = 512, message = "部门描述长度不能超过512")
    private String description;

    /**
     * 父部门ID。
     * 系统仅允许一个根，新建时必须指定父部门。
     */
    @NotNull(message = "父部门不能为空")
    private Long parentId;
}
