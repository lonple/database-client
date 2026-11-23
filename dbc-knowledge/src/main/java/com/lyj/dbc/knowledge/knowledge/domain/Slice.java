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
@TableName(value = "t_knowledge_slice", autoResultMap = true)
public class Slice {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long documentId;
    private Integer seqNo;
    private String title;
    /** 切片说明；参与稠密向量 */
    private String description;
    /** 正文摘要；参与稠密向量 */
    private String bodySummary;
    private String body;
    @TableField(typeHandler = PgTextArrayTypeHandler.class)
    private List<String> techTags;
    /** HORIZONTAL | VERTICAL；同一原文可混有两种 */
    private String orientation;
    private Long categoryId;
    private String status;
    /** 与所属原文同一次发布共享的版本号 */
    private Integer versionNo;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private OffsetDateTime publishedAt;
}
