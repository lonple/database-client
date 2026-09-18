package com.lyj.dbc.client.manage;

import com.lyj.dbc.client.common.ApiResponse;
import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.common.MtlsRestClientFactory;
import com.lyj.dbc.client.manage.dto.ManageInnerDtos;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Objects;

/**
 * manage inner API 客户端（供 sqlwork 等调用）。
 * <p>
 * 当前转发终端用户 Authorization；后续可升级为 mTLS + 服务签名。
 */
public class ManageInnerClient {

    private final RestClient restClient;
    private final String baseUrl;

    public ManageInnerClient(ManageInnerClientProperties properties) {
        Objects.requireNonNull(properties, "properties");
        this.baseUrl = MtlsRestClientFactory.trimTrailingSlash(properties.getBaseUrl());
        this.restClient = RestClient.builder().build();
    }

    public ManageInnerClient(RestClient restClient, String baseUrl) {
        this.restClient = Objects.requireNonNull(restClient, "restClient");
        this.baseUrl = MtlsRestClientFactory.trimTrailingSlash(baseUrl);
    }

    public List<ManageInnerDtos.WorkspaceSummary> listMyWorkspaces(String authorizationHeader) {
        ApiResponse<List<ManageInnerDtos.WorkspaceSummary>> resp = restClient.get()
                .uri(baseUrl + "/inner/sqlwork/workspaces/mine")
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
        return requireData(resp, "拉取我的工作空间失败");
    }

    public List<ManageInnerDtos.ConnectionSummary> listWorkspaceConnections(Long workspaceId,
                                                                            String authorizationHeader) {
        ApiResponse<List<ManageInnerDtos.ConnectionSummary>> resp = restClient.get()
                .uri(baseUrl + "/inner/sqlwork/workspaces/{id}/connections", workspaceId)
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
        return requireData(resp, "拉取空间连接失败");
    }

    public ManageInnerDtos.ConnectionMaterial getConnectionMaterial(Long connectionId,
                                                                    String authorizationHeader) {
        ApiResponse<ManageInnerDtos.ConnectionMaterial> resp = restClient.get()
                .uri(baseUrl + "/inner/sqlwork/connections/{id}/material", connectionId)
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
        return requireData(resp, "拉取连接材料失败");
    }

    public ManageInnerDtos.AuthzEvaluateResult evaluate(ManageInnerDtos.AuthzEvaluateRequest request,
                                                        String authorizationHeader) {
        ApiResponse<ManageInnerDtos.AuthzEvaluateResult> resp = restClient.post()
                .uri(baseUrl + "/inner/sqlwork/authz/evaluate")
                .header(HttpHeaders.AUTHORIZATION, authorizationHeader)
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
        return requireData(resp, "鉴权裁决失败");
    }

    private static <T> T requireData(ApiResponse<T> resp, String fallback) {
        if (resp == null || !resp.isSuccess() || resp.getData() == null) {
            throw new InnerClientException(resp == null ? fallback : resp.getMessage(),
                    resp == null ? -1 : resp.getCode());
        }
        return resp.getData();
    }
}
