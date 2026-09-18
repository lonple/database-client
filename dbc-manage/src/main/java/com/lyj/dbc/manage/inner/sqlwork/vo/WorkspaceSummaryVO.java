package com.lyj.dbc.manage.inner.sqlwork.vo;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 工作空间摘要（JSON 字段 role 与 sqlwork 客户端对齐）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WorkspaceSummaryVO {

    private Long id;
    private String name;
    private String description;
    private String spaceType;

    @JsonProperty("role")
    private String myRole;
}
