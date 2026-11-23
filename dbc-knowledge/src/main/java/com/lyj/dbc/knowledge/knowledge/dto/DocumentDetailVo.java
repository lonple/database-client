package com.lyj.dbc.knowledge.knowledge.dto;

import lombok.Data;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class DocumentDetailVo {
    private Long id;
    private String title;
    private String productName;
    private String orientation;
    private String sourceType;
    private String body;
    private String status;
    private Long categoryId;
    private String categoryPath;
    private String summary;
    private Long lineageId;
    private Integer versionNo;
    private String updateMode;
    private Long replacesDocumentId;
    private List<Long> expireSliceIds = new ArrayList<>();
    private String vectorSyncStatus;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private OffsetDateTime publishedAt;
    private List<SliceVo> slices = new ArrayList<>();
}
