package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class CanvasVo {
    private Long graphId;
    private String name;
    private String summary;
    private List<NodeVo> nodes = new ArrayList<>();
    private List<EdgeVo> edges = new ArrayList<>();
}
