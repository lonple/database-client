package com.lyj.dbc.usercenter.app.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 应用签名公钥实体，对应表 t_usercenter_app_key。
 */
@Data
@TableName("t_usercenter_app_key")
public class AppKeyEntity {

    /** 主键 */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 所属应用 clientId */
    private String clientId;

    /** 密钥 ID */
    private String kid;

    /** 算法，如 ES256 */
    private String algorithm;

    /** 公钥 PEM */
    private String publicKeyPem;

    /** 私钥经 KEK 加密后的密文（中心代签；对接 KMS 后可改为引用） */
    private String privateKeyCipher;

    /** 注册实例标识 */
    private String instanceId;

    /**
     * 状态。
     * active：可用；revoked：已吊销
     */
    private String status;

    /**
     * 逻辑删除。
     * 0：未删除；1：已删除
     */
    @TableLogic
    private Integer deleted;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 最近心跳时间 */
    private OffsetDateTime lastSeenAt;

    /** 吊销时间 */
    private OffsetDateTime revokedAt;
}
