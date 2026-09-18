package com.lyj.dbc.client.usercenter.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 部门树节点（与 usercenter DeptTreeNodeVO 对齐）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeptTreeNode {

    private Long id;
    private String name;
    private String description;
    private Long parentId;
    private Integer level;
    private String path;

    @Builder.Default
    private List<DeptTreeNode> children = new ArrayList<>();
}
