package com.lyj.dbc.usercenter.app.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 中心代签请求：由中心组装 stringToSign。
 */
@Data
public class AppKeySignRequest {

    /** 实例 ID，用于选择该实例当前存活密钥 */
    @NotBlank
    @Size(max = 128)
    private String instanceId;

    /** HTTP 方法 */
    @NotBlank
    @Size(max = 16)
    private String method;

    /** 被调方收到的 path */
    @NotBlank
    @Size(max = 2048)
    private String path;

    /** 原始 queryString，可空 */
    @Size(max = 4096)
    private String query;

    /** Unix 秒时间戳 */
    @NotBlank
    @Size(max = 32)
    private String timestamp;

    /** 防重放随机串 */
    @NotBlank
    @Size(max = 128)
    private String nonce;

    /** body 的 SHA-256 十六进制；无 body 则为空串哈希 */
    @NotBlank
    @Size(max = 128)
    private String bodySha256Hex;
}
