package com.lyj.dbc.sqlwork.client;

import com.lyj.dbc.sqlwork.api.dto.AuthzEvaluateRequest;
import com.lyj.dbc.sqlwork.api.vo.AuthzEvaluateResult;
import com.lyj.dbc.sqlwork.api.vo.ConnectionMaterial;
import com.lyj.dbc.sqlwork.api.vo.ConnectionSummaryVO;
import com.lyj.dbc.sqlwork.api.vo.MyWorkspaceAuthzVO;
import com.lyj.dbc.sqlwork.api.vo.WorkspaceSummaryVO;
import com.lyj.dbc.sqlwork.common.ApiResponse;
import com.lyj.dbc.sqlwork.common.BizException;
import com.lyj.dbc.sqlwork.config.SqlworkProperties;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Collections;
import java.util.List;

/**
 * 调用 manage inner 接口（{@code http://dbc-manage} + Nacos LoadBalancer）。
 */
@Component
public class ManageClient {

    private final RestClient restClient;

    public ManageClient(SqlworkProperties properties,
                        @Qualifier("loadBalancedRestClientBuilder") RestClient.Builder loadBalancedRestClientBuilder) {
        this.restClient = loadBalancedRestClientBuilder
                .baseUrl(trimTrailingSlash(properties.getManageBaseUrl()))
                .build();
    }

    public List<WorkspaceSummaryVO> listMyWorkspaces(String authorizationHeader) {
        ApiResponse<List<WorkspaceSummaryVO>> resp = restClient.get()
                .uri("/inner/sqlwork/workspaces/mine")
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<List<WorkspaceSummaryVO>>>() {});
        return unwrapList(resp);
    }

    public List<ConnectionSummaryVO> listWorkspaceConnections(Long workspaceId, String authorizationHeader) {
        ApiResponse<List<ConnectionSummaryVO>> resp = restClient.get()
                .uri("/inner/sqlwork/workspaces/{workspaceId}/connections", workspaceId)
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<List<ConnectionSummaryVO>>>() {});
        return unwrapList(resp);
    }

    public MyWorkspaceAuthzVO getMyAuthz(Long workspaceId, String authorizationHeader) {
        ApiResponse<MyWorkspaceAuthzVO> resp = restClient.get()
                .uri("/inner/sqlwork/workspaces/{workspaceId}/my-authz", workspaceId)
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<MyWorkspaceAuthzVO>>() {});
        MyWorkspaceAuthzVO data = unwrap(resp);
        if (data == null) {
            throw BizException.notFound("授权信息不存在");
        }
        return data;
    }

    public ConnectionMaterial getMaterial(Long connectionId, String authorizationHeader) {
        ApiResponse<ConnectionMaterial> resp = restClient.get()
                .uri("/inner/sqlwork/connections/{connectionId}/material", connectionId)
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<ConnectionMaterial>>() {});
        ConnectionMaterial data = unwrap(resp);
        if (data == null) {
            throw BizException.notFound("连接凭证不存在: " + connectionId);
        }
        return data;
    }

    public AuthzEvaluateResult evaluate(AuthzEvaluateRequest request, String authorizationHeader) {
        ApiResponse<AuthzEvaluateResult> resp = restClient.post()
                .uri("/inner/sqlwork/authz/evaluate")
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<AuthzEvaluateResult>>() {});
        AuthzEvaluateResult data = unwrap(resp);
        if (data == null) {
            throw BizException.badRequest("鉴权裁决无响应");
        }
        return data;
    }

    private static <T> T unwrap(ApiResponse<T> resp) {
        if (resp == null) {
            throw BizException.badRequest("manage 无响应");
        }
        if (resp.getCode() != 0) {
            throw BizException.badRequest(resp.getMessage() == null ? "manage 调用失败" : resp.getMessage());
        }
        return resp.getData();
    }

    private static <T> List<T> unwrapList(ApiResponse<List<T>> resp) {
        List<T> data = unwrap(resp);
        return data == null ? Collections.emptyList() : data;
    }

    private static String trimTrailingSlash(String url) {
        if (url == null || url.isBlank()) {
            return url;
        }
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
