package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

/**
 * 一条外键边：本表字段指向对端表字段。
 */
@Data
public class TableRelationEdgeVo {
    private String fromTable;
    private String fromColumn;
    private String toTable;
    private String toColumn;
}
