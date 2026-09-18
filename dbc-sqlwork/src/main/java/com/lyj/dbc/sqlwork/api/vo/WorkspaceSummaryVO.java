package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 工作空间摘要（我的空间列表项）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class WorkspaceSummaryVO {

    private Long id;
    private String name;
    private String description;
    private String spaceType;
    private String role;
}
