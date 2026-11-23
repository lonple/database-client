package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class TableRelationVo {
    private String fromTable;
    private String toTable;
    private int pathLength;
    private List<Map<String, Object>> joins;
    private List<String> joinTexts;
    /** 由 joins / joinTexts 整理出的外键边，方向与图谱列一致。 */
    private List<TableRelationEdgeVo> edges;
}
