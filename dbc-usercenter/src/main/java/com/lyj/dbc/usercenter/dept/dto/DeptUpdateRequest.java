package com.lyj.dbc.usercenter.dept.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 更新部门请求（含整部门迁移：修改 parentId）。
 */
@Data
public class DeptUpdateRequest {

    /** 部门名称 */
    @NotBlank(message = "部门名称不能为空")
    @Size(max = 64, message = "部门名称长度不能超过64")
    private String name;

    /** 部门描述，可选 */
    @Size(max = 512, message = "部门描述长度不能超过512")
    private String description;

    /**
     * 父部门ID。
     * 根部门必须为 null；非根必须指定且不可指向自身或子孙。
     */
    private Long parentId;
}
