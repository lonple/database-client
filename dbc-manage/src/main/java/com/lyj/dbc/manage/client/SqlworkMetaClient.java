package com.lyj.dbc.manage.client;

import com.lyj.dbc.manage.authz.meta.vo.MetaTablePageVO;
import com.lyj.dbc.manage.asset.connection.vo.ConnectionPingResultVO;
import com.lyj.dbc.manage.common.ApiResponse;
import com.lyj.dbc.manage.common.BizException;
import com.lyj.dbc.manage.config.ManageProperties;
import com.lyj.dbc.manage.inner.sqlwork.vo.ConnectionMaterialVO;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.util.List;

/**
 * 调用 sqlwork /inner/meta/**：转发终端用户 JWT，供工作空间授权选表（不做成员表过滤）。
 */
@Component
public class SqlworkMetaClient {

    private final RestClient restClient;

    public SqlworkMetaClient(ManageProperties properties,
                             @org.springframework.beans.factory.annotation.Qualifier("loadBalancedRestClientBuilder")
                             RestClient.Builder loadBalancedRestClientBuilder) {
        this.restClient = loadBalancedRestClientBuilder
                .baseUrl(trimTrailingSlash(properties.getSqlworkBaseUrl()))
                .build();
    }

    public List<String> listDatabases(Long connectionId) {
        ApiResponse<List<String>> body = get(
                uriBuilder -> uriBuilder.path("/inner/meta/databases")
                        .queryParam("connectionId", connectionId)
                        .build(),
                new ParameterizedTypeReference<>() {
                });
        return requireData(body, "查询数据库列表失败");
    }

    public List<String> listSchemas(Long connectionId, String database) {
        ApiResponse<List<String>> body = get(
                uriBuilder -> {
                    var b = uriBuilder.path("/inner/meta/schemas")
                            .queryParam("connectionId", connectionId);
                    if (database != null && !database.isBlank()) {
                        b.queryParam("database", database);
                    }
                    return b.build();
                },
                new ParameterizedTypeReference<>() {
                });
        return requireData(body, "查询模式列表失败");
    }

    public MetaTablePageVO listTables(Long connectionId, String database, String schema,
                                      String keyword, int page, int size) {
        ApiResponse<MetaTablePageVO> body = get(
                uriBuilder -> {
                    var b = uriBuilder.path("/inner/meta/tables")
                            .queryParam("connectionId", connectionId)
                            .queryParam("page", page)
                            .queryParam("size", size);
                    if (database != null && !database.isBlank()) {
                        b.queryParam("database", database);
                    }
                    if (schema != null && !schema.isBlank()) {
                        b.queryParam("schema", schema);
                    }
                    if (keyword != null && !keyword.isBlank()) {
                        b.queryParam("keyword", keyword);
                    }
                    return b.build();
                },
                new ParameterizedTypeReference<>() {
                });
        return requireData(body, "查询表列表失败");
    }

    /**
     * 草稿材料探活（manage 组装 jdbcUrl/账号后转发，sqlwork 执行短超时 SELECT）。
     */
    public ConnectionPingResultVO ping(ConnectionMaterialVO material) {
        try {
            ApiResponse<ConnectionPingResultVO> body = restClient.post()
                    .uri("/inner/connections/ping")
                    .header(HttpHeaders.AUTHORIZATION, requireBearerHeader())
                    .contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(material)
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {
                    });
            return requireData(body, "连接测试失败");
        } catch (RestClientResponseException ex) {
            throw BizException.badRequest(extractRemoteMessage(ex));
        } catch (RestClientException ex) {
            throw new BizException(org.springframework.http.HttpStatus.BAD_GATEWAY,
                    "无法连接 sqlwork：" + ex.getMessage());
        }
    }

    private <T> ApiResponse<T> get(java.util.function.Function<
            org.springframework.web.util.UriBuilder, java.net.URI> uriFunction,
                                   ParameterizedTypeReference<ApiResponse<T>> type) {
        try {
            return restClient.get()
                    .uri(uriFunction)
                    .header(HttpHeaders.AUTHORIZATION, requireBearerHeader())
                    .accept(MediaType.APPLICATION_JSON)
                    .retrieve()
                    .body(type);
        } catch (RestClientResponseException ex) {
            throw BizException.badRequest(extractRemoteMessage(ex));
        } catch (RestClientException ex) {
            throw new BizException(org.springframework.http.HttpStatus.BAD_GATEWAY,
                    "无法连接 sqlwork 元数据服务：" + ex.getMessage());
        }
    }

    private static String requireBearerHeader() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getCredentials() instanceof String token)
                || token.isBlank()) {
            throw BizException.unauthorized("未登录或令牌无效");
        }
        return token.startsWith("Bearer ") ? token : "Bearer " + token;
    }

    private static <T> T requireData(ApiResponse<T> body, String fallbackMessage) {
        if (body == null || body.getCode() != 0 || body.getData() == null) {
            throw BizException.badRequest(body == null ? fallbackMessage : body.getMessage());
        }
        return body.getData();
    }

    private static String extractRemoteMessage(RestClientResponseException ex) {
        String raw = ex.getResponseBodyAsString();
        if (raw == null || raw.isBlank()) {
            return "sqlwork 元数据查询失败（HTTP " + ex.getStatusCode().value() + "）";
        }
        // 尽量透传业务文案；解析失败则截断原文
        int msgIdx = raw.indexOf("\"message\"");
        if (msgIdx >= 0) {
            int colon = raw.indexOf(':', msgIdx);
            int q1 = raw.indexOf('"', colon + 1);
            int q2 = raw.indexOf('"', q1 + 1);
            if (q1 >= 0 && q2 > q1) {
                return raw.substring(q1 + 1, q2);
            }
        }
        return raw.length() > 200 ? raw.substring(0, 200) : raw;
    }

    private static String trimTrailingSlash(String url) {
        if (url == null || url.isBlank()) {
            return url;
        }
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
