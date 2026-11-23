package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 单表列清单（批量 columns 响应项）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TableColumnsVO {
    private String table;
    private String schema;
    private List<ColumnVO> columns;
    /** 单表失败时的可读原因；成功时为空 */
    private String error;
}
