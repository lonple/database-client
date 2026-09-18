package com.lyj.dbc.client.usercenter;

import lombok.Builder;
import lombok.Data;

import java.nio.file.Path;

/**
 * 调用 usercenter mTLS inner 的配置。
 */
@Data
@Builder
public class UserCenterInnerClientProperties {

    /** discovery://dbc-usercenter 或 https://host:port 逃生舱 */
    private String mtlsBaseUrl;

    /** 本服务 clientId，如 dbc-manage */
    private String clientId;

    /** secrets 根目录 */
    private Path secretsDir;
}
