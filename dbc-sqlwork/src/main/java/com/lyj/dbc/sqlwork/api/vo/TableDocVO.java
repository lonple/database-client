package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 单表文档：供知识库等场景生成 Markdown。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TableDocVO {
    /** 英文表名（知识库标题） */
    private String name;
    private String schema;
    private String objectType;
    /** 表中文说明（知识库简介） */
    private String comment;
    @Builder.Default
    private List<ColumnVO> columns = new ArrayList<>();
    /** 已拼好的 Markdown 正文 */
    private String markdown;
}
