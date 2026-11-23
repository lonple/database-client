package com.lyj.dbc.graph.graphmeta.dto;

import lombok.Data;

@Data
public class GraphUpdateRequest {
    private Long categoryId;
    private String code;
    private String name;
    private String summary;
    private String productName;
}
