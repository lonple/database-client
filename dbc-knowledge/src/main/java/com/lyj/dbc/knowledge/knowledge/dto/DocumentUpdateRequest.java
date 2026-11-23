package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class DocumentUpdateRequest {
    private String title;
    private String productName;
    private String orientation;
    private List<String> orientations = new ArrayList<>();
    private String body;
    private String summary;
    private Long categoryId;
    private String updateMode;
    private Long replacesDocumentId;
    private List<Long> expireSliceIds;
}
