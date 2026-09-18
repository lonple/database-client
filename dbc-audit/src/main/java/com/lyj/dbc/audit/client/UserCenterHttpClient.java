package com.lyj.dbc.audit.client;

import com.lyj.dbc.audit.client.dto.UserMeVO;
import com.lyj.dbc.audit.common.ApiResponse;
import com.lyj.dbc.audit.common.BizException;
import com.lyj.dbc.audit.config.AuditProperties;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * 调用 usercenter 公开鉴权接口（{@code http://dbc-usercenter} + Nacos LoadBalancer）。
 */
@Component
public class UserCenterHttpClient {

    private final RestClient restClient;

    public UserCenterHttpClient(AuditProperties properties,
                                @Qualifier("loadBalancedRestClientBuilder") RestClient.Builder loadBalancedRestClientBuilder) {
        this.restClient = loadBalancedRestClientBuilder
                .baseUrl(trimTrailingSlash(properties.getUsercenterBaseUrl()))
                .build();
    }

    public UserMeVO fetchMe(String bearerToken) {
        ApiResponse<UserMeVO> body = restClient.get()
                .uri("/auth/me")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + bearerToken)
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<UserMeVO>>() {});
        return requireData(body, "拉取当前用户失败");
    }

    private static <T> T requireData(ApiResponse<T> body, String fallbackMessage) {
        if (body == null || body.getCode() != 0 || body.getData() == null) {
            throw BizException.unauthorized(body == null ? fallbackMessage : body.getMessage());
        }
        return body.getData();
    }

    private static String trimTrailingSlash(String url) {
        if (url == null || url.isBlank()) {
            return url;
        }
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
