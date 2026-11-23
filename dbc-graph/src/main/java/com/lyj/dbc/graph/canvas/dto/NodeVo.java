package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

import java.util.Map;

@Data
public class NodeVo {
    private String nodeId;
    private String name;
    private String nodeType;
    private String description;
    /** 一级属性：男 / 女；人物节点用于父母边解读称谓。 */
    private String gender;
    private Map<String, Object> props;
    private String refKind;
    private Long refId;
    private double x;
    private double y;
}
