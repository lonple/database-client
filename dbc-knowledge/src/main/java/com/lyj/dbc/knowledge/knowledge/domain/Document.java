package com.lyj.dbc.knowledge.knowledge.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@TableName("t_knowledge_document")
public class Document {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String title;
    /** 产品名；检索过滤标量 */
    private String productName;
    private String orientation;
    private String sourceType;
    private String body;
    private String status;
    private Long categoryId;
    /** 原文简介（必填）；参与原文摘要向量 */
    private String summary;
    private String createdBy;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private OffsetDateTime publishedAt;
    /** NONE | PENDING | SYNCED | UNSYNCED */
    private String vectorSyncStatus;
    /** 版本脉络 id；新建后默认等于自身 id */
    private Long lineageId;
    /** 同一次发布共享的版本号 */
    private Integer versionNo;
    /** CREATE | REPLACE_DOCUMENT | REPLACE_SLICES */
    private String updateMode;
    /** 更新目标已发布原文 */
    private Long replacesDocumentId;
    /** JSON 数组字符串，REPLACE_SLICES 时待过期切片 id */
    private String expireSliceIds;
}
