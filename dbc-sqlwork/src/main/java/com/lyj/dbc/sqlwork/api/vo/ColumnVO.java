package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 表列元数据。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ColumnVO {
    private String name;
    private String dataType;
    private boolean nullable;
    private String comment;
    private int ordinal;
}
