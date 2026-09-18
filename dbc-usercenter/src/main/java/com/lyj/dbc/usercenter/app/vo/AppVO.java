package com.lyj.dbc.usercenter.app.vo;

import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 应用列表展示。
 */
@Data
public class AppVO {

    /** 主键 */
    private Long id;

    /** clientId */
    private String clientId;

    /** 应用名称 */
    private String appName;

    /** 是否内置 */
    private Integer builtin;

    /** 状态：1启用 0停用 */
    private Integer status;

    /** 是否已签发 mTLS 客户端证书 */
    private Boolean hasClientCert;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 更新时间 */
    private OffsetDateTime updatedAt;
}
