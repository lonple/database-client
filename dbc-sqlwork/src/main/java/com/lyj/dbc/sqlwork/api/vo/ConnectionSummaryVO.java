package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 空间下可用连接摘要。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionSummaryVO {

    private Long connectionId;
    private String name;
    private String dbType;
}
