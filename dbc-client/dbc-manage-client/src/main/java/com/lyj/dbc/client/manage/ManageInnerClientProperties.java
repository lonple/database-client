package com.lyj.dbc.client.manage;

import lombok.Builder;
import lombok.Data;

/**
 * 调用 manage inner 的配置（当前以 HTTP + 用户 JWT 转发为主；后续可升级 mTLS/签名）。
 */
@Data
@Builder
public class ManageInnerClientProperties {

    /** http://host:8006 或经网关可达的 manage 基址 */
    private String baseUrl;
}
