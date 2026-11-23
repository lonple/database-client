package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

@Data
public class EdgeVo {
    private String edgeId;
    private String fromNodeId;
    private String toNodeId;
    private String relType;
    private String description;
}
