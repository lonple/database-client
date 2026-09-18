package com.lyj.dbc.manage.inner.sqlwork.vo;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 空间下可用连接摘要（JSON 字段 connectionId 与 sqlwork 客户端对齐）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionSummaryVO {

    @JsonProperty("connectionId")
    private Long id;

    private String name;
    private String dbType;
}
