package com.lyj.dbc.manage.asset.connection.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 连接探活结果（透传 sqlwork）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionPingResultVO {

    private boolean success;
    private long latencyMs;
    private String message;
}
