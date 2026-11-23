package com.lyj.dbc.graph.graphmeta.dto;

import lombok.Data;

@Data
public class TableRelationImportRequest {
    /** Markdown 正文（必填） */
    private String markdown;
    /** 覆盖 MD 内 code */
    private String code;
    /** 覆盖 MD 内 name */
    private String name;
    /** 覆盖 MD 内 summary */
    private String summary;
    /** 覆盖 MD 内 productName */
    private String productName;
    /** 编码已存在时是否删除重建，默认 false */
    private Boolean force;
}
