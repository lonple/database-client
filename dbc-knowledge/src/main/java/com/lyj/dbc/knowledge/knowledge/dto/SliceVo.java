package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class SliceVo {
    private Long id;
    private Long documentId;
    private Integer seqNo;
    private String title;
    private String description;
    private String bodySummary;
    private String body;
    private List<String> techTags = new ArrayList<>();
    private String orientation;
    private Long categoryId;
    private String categoryPath;
    private String status;
    private Integer versionNo;
    private OffsetDateTime publishedAt;
}
