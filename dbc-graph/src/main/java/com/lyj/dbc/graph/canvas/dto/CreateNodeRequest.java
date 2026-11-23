package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

import java.util.Map;

@Data
public class CreateNodeRequest {
    private String name;
    private String nodeType;
    private String description;
    /** 一级属性：男 / 女（也可写在 props.gender，服务端会提升为节点属性）。 */
    private String gender;
    private Map<String, Object> props;
    private String refKind;
    private Long refId;
    private Double x;
    private Double y;
}
