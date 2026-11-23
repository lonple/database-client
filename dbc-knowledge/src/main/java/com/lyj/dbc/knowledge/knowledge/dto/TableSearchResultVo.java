package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;

@Data
public class TableSearchResultVo {
    private String query;
    private String titleQuery;
    private String descriptionQuery;
    private String bodySummaryQuery;
    private String ftsQuery;
    private List<TableSearchHit> tables;
    private List<TableRelationVo> tableRelations;
}
