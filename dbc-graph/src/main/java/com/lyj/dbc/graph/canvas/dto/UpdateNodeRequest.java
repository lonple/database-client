package com.lyj.dbc.graph.canvas.dto;

import lombok.Data;

import java.util.Map;

@Data
public class UpdateNodeRequest {
    private String name;
    private String nodeType;
    private String description;
    /** 一级属性：男 / 女；传空串可清空。 */
    private String gender;
    private Map<String, Object> props;
    private String refKind;
    private Long refId;
}
