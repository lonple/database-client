package com.lyj.dbc.knowledge.knowledge.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class DocumentCreateRequest {
    @NotBlank
    private String title;
    /** 产品名，检索过滤 */
    private String productName;
    /** HORIZONTAL / VERTICAL / BOTH；与 orientations 二选一，列表优先 */
    private String orientation;
    private List<String> orientations = new ArrayList<>();
    private String body = "";
    /** 原文简介，必填 */
    @NotBlank
    private String summary;
    private String sourceType;
    private Long categoryId;
    private String createdBy;
    /** CREATE | REPLACE_DOCUMENT | REPLACE_SLICES */
    private String updateMode;
    /** 更新目标已发布原文 id */
    private Long replacesDocumentId;
    /** REPLACE_SLICES：待过期切片 id */
    private List<Long> expireSliceIds = new ArrayList<>();
}
