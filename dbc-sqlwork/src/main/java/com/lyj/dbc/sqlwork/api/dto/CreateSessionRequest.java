package com.lyj.dbc.sqlwork.api.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 创建工作台会话。
 */
@Data
public class CreateSessionRequest {

    @NotNull
    private Long workspaceId;

    @NotNull
    private Long connectionId;

    private String database;
    private String schema;

    /** 手动提交模式；默认 false（自动提交） */
    private Boolean manualMode;
}
