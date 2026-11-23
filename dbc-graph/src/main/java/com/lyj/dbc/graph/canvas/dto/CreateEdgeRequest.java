package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

@Data
public class CreateEdgeRequest {
    private String fromNodeId;
    private String toNodeId;
    private String relType;
    private String description;
}
