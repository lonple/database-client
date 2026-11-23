package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;

@Data
public class TableRelationQueryResultVo {
    private Long graphId;
    private String table;
    private List<TableRelationVo> tableRelations;
}
