package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class CategoryTreeNode {
    private Long id;
    private Long parentId;
    private String name;
    private String code;
    private String path;
    private Integer sortNo;
    private List<CategoryTreeNode> children = new ArrayList<>();
}
