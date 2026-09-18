package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 目标库连接探活结果。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConnectionPingResult {

    /** 是否连通 */
    private boolean success;

    /** 耗时（毫秒） */
    private long latencyMs;

    /** 说明（失败时含错误摘要） */
    private String message;

    public static ConnectionPingResult ok(long latencyMs) {
        return new ConnectionPingResult(true, latencyMs, "连接成功");
    }

    public static ConnectionPingResult fail(long latencyMs, String message) {
        return new ConnectionPingResult(false, latencyMs, message == null ? "连接失败" : message);
    }
}
