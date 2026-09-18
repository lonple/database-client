package com.lyj.dbc.usercenter.app.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.OffsetDateTime;

/**
 * 微服务应用实体，对应表 t_usercenter_app。
 */
@Data
@TableName("t_usercenter_app")
public class AppEntity {

    /** 主键 */
    @TableId(type = IdType.AUTO)
    private Long id;

    /** 应用客户端ID，唯一 */
    private String clientId;

    /** 应用显示名称 */
    private String appName;

    /**
     * 是否内置。
     * 1：是；0：否
     */
    private Integer builtin;

    /**
     * 状态。
     * 1：启用；0：停用
     */
    private Integer status;

    /** 历史字段：曾存 clientSecret 密文；现鉴权改 mTLS，不再读写 */
    private String secretCipher;

    /**
     * 逻辑删除。
     * 0：未删除；1：已删除
     */
    @TableLogic
    private Integer deleted;

    /** 创建时间 */
    private OffsetDateTime createdAt;

    /** 更新时间 */
    private OffsetDateTime updatedAt;
}
