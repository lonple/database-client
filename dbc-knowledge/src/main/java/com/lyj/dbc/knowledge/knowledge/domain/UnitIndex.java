package com.lyj.dbc.knowledge.knowledge.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.lyj.dbc.knowledge.knowledge.support.PgTextArrayTypeHandler;
import lombok.Data;

import java.time.OffsetDateTime;
import java.util.List;

@Data
@TableName(value = "t_knowledge_unit_index", autoResultMap = true)
public class UnitIndex {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String kind;
    private Long refId;
    private Long documentId;
    private String title;
    /** DOCUMENT=原文简介；SLICE=切片说明 */
    private String description;
    /** SLICE=正文摘要；DOCUMENT 为空 */
    private String bodySummary;
    private String body;
    private Long categoryId;
    private String status;
    @TableField(typeHandler = PgTextArrayTypeHandler.class)
    private List<String> techTags;
    private OffsetDateTime updatedAt;

    /** 切片所属原文标题（非表字段，列表/详情展示用） */
    @TableField(exist = false)
    private String documentTitle;

    /** 所属原文的产品名（非表字段，列表展示用） */
    @TableField(exist = false)
    private String productName;
}
