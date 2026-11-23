package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

@Data
public class CategoryCreateRequest {
    private Long parentId;
    private String name;
    /** 问数检索用的稳定编码，如 METADATA / GENERAL / QUESTION。 */
    private String code;
    private Integer sortNo;
}
