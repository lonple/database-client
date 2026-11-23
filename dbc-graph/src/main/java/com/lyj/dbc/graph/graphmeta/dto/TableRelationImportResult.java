package com.lyj.dbc.graph.graphmeta.dto;

import com.lyj.dbc.graph.graphmeta.entity.GraphEntity;
import lombok.Data;

@Data
public class TableRelationImportResult {
    private GraphEntity graph;
    private int tableCount;
    private int fkCount;
    private int nodeCount;
    private int edgeCount;
    private boolean replaced;
}
