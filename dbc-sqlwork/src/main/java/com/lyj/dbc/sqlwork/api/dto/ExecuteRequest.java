package com.lyj.dbc.sqlwork.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * SQL 执行请求。
 */
@Data
public class ExecuteRequest {

    @NotNull(message = "workspaceId 不能为空")
    private Long workspaceId;

    @NotNull(message = "connectionId 不能为空")
    private Long connectionId;

    @NotBlank(message = "sql 不能为空")
    private String sql;

    /** 最大返回行数；空则用配置默认值 */
    private Integer maxRows;

    /** 可选：目标库（切换 JDBC database） */
    private String database;

    /** 可选：默认 schema（如 PG search_path） */
    private String schema;

    /** 工作台会话 ID（手动事务 / Tab 生命周期） */
    private String sessionId;
}
