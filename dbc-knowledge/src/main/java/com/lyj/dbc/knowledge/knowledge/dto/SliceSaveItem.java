package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class SliceSaveItem {
    private Long id;
    private String title;
    private String description;
    private String bodySummary;
    private String body;
    private List<String> techTags = new ArrayList<>();
    /** HORIZONTAL | VERTICAL */
    private String orientation;
    private Long categoryId;
    private Integer seqNo;
}
