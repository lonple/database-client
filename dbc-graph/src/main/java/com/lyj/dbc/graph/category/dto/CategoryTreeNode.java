package com.lyj.dbc.graph.category.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class CategoryTreeNode {
    private Long id;
    private Long parentId;
    private String name;
    private Integer sortNo;
    private List<CategoryTreeNode> children = new ArrayList<>();
}
