package com.lyj.dbc.sqlwork.api.dto;

import lombok.Data;

import java.util.List;

/**
 * 多表列元数据批量查询。
 */
@Data
public class ColumnsBatchRequest {
    private Long workspaceId;
    private Long connectionId;
    private String database;
    private String schema;
    /** 表名列表；单次上限由服务端截断（默认 20） */
    private List<String> tables;
}
