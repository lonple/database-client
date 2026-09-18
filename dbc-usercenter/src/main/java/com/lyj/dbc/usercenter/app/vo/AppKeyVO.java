package com.lyj.dbc.usercenter.app.vo;

import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 应用公钥展示。
 */
@Data
public class AppKeyVO {

    /** 主键 */
    private Long id;

    /** clientId */
    private String clientId;

    /** kid */
    private String kid;

    /** 算法 */
    private String algorithm;

    /** 公钥 PEM */
    private String publicKeyPem;

    /** 实例 ID */
    private String instanceId;

    /** 状态 */
    private String status;

    /** 是否心跳未过期（可用于验签） */
    private Boolean alive;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 最近心跳 */
    private OffsetDateTime lastSeenAt;

    /** 吊销时间 */
    private OffsetDateTime revokedAt;
}
