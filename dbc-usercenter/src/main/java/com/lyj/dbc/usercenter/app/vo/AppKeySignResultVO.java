package com.lyj.dbc.usercenter.app.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 代签结果。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AppKeySignResultVO {

    /** 使用的 kid */
    private String kid;

    /** Base64URL 签名 */
    private String signature;

    /** 回显时间戳 */
    private String timestamp;

    /** 回显 nonce */
    private String nonce;
}
