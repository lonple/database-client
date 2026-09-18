package com.lyj.dbc.manage.asset.instance.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class InstanceUpdateRequest {

    @NotBlank(message = "实例名称不能为空")
    @Size(max = 128)
    private String name;

    /** 公司域必填；个人域忽略 */
    private Long deptId;

    @NotBlank(message = "库类型不能为空")
    private String dbType;

    @NotBlank(message = "主机不能为空")
    @Size(max = 255)
    private String host;

    @NotNull(message = "端口不能为空")
    @Min(1)
    @Max(65535)
    private Integer port;

    @Size(max = 255)
    private String driverClassName;

    @Min(0)
    @Max(1)
    private Integer status;

    @Size(max = 512)
    private String description;
}
