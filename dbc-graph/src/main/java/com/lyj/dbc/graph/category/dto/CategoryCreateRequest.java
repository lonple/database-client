package com.lyj.dbc.graph.category.dto;

import lombok.Data;

@Data
public class CategoryCreateRequest {
    private Long parentId;
    private String name;
    private Integer sortNo;
}
