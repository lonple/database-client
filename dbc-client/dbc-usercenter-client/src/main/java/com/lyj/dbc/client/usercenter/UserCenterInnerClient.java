package com.lyj.dbc.client.usercenter;

import com.lyj.dbc.client.common.ApiResponse;
import com.lyj.dbc.client.common.DiscoveryHttpsBaseUrlResolver;
import com.lyj.dbc.client.common.InnerClientException;
import com.lyj.dbc.client.common.MtlsRestClientFactory;
import com.lyj.dbc.client.common.PageResult;
import com.lyj.dbc.client.usercenter.dto.DeptTreeNode;
import com.lyj.dbc.client.usercenter.dto.PermissionRegisterItem;
import com.lyj.dbc.client.usercenter.dto.UserSummary;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Supplier;

/**
 * usercenter inner API 客户端（mTLS）。基址支持 {@code discovery://dbc-usercenter}（Nacos + mtls-port）。
 */
public class UserCenterInnerClient {

    private final RestClient restClient;
    private final Supplier<String> baseUrlSupplier;

    public UserCenterInnerClient(UserCenterInnerClientProperties properties) {
        this(properties, null);
    }

    public UserCenterInnerClient(UserCenterInnerClientProperties properties,
                                 DiscoveryHttpsBaseUrlResolver discoveryResolver) {
        Objects.requireNonNull(properties, "properties");
        this.restClient = MtlsRestClientFactory.create(properties.getSecretsDir(), properties.getClientId());
        String configured = properties.getMtlsBaseUrl();
        if (discoveryResolver != null) {
            this.baseUrlSupplier = () -> discoveryResolver.resolveHttpsBaseUrl(configured);
        } else {
            String fixed = MtlsRestClientFactory.trimTrailingSlash(configured);
            this.baseUrlSupplier = () -> fixed;
        }
    }

    public UserCenterInnerClient(RestClient restClient, String mtlsBaseUrl) {
        this.restClient = Objects.requireNonNull(restClient, "restClient");
        String fixed = MtlsRestClientFactory.trimTrailingSlash(mtlsBaseUrl);
        this.baseUrlSupplier = () -> fixed;
    }

    private String baseUrl() {
        return baseUrlSupplier.get();
    }

    /** GET /inner/depts/tree */
    public List<DeptTreeNode> listDeptTree() {
        ApiResponse<List<DeptTreeNode>> resp = restClient.get()
                .uri(baseUrl() + "/inner/depts/tree")
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<List<DeptTreeNode>>>() {});
        return requireData(resp, "拉取部门树失败");
    }

    /** GET /inner/users */
    public PageResult<UserSummary> pageUsers(long page, long size, String username) {
        UriComponentsBuilder builder = UriComponentsBuilder
                .fromUriString(baseUrl() + "/inner/users")
                .queryParam("page", page)
                .queryParam("size", size);
        if (username != null && !username.isBlank()) {
            builder.queryParam("username", username.trim());
        }
        ApiResponse<PageResult<UserSummary>> resp = restClient.get()
                .uri(builder.build(true).toUri())
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<PageResult<UserSummary>>>() {});
        return requireData(resp, "拉取用户列表失败");
    }

    /** POST /inner/permissions/register */
    public void registerPermissions(List<PermissionRegisterItem> permissions) {
        Map<String, Object> body = new HashMap<>();
        body.put("permissions", permissions);
        postVoid("/inner/permissions/register", body, "权限注册失败");
    }

    /** POST /inner/permissions/bind-roles */
    public void bindPermissionsToRoles(List<String> roleCodes, List<String> permissionCodes) {
        Map<String, Object> body = new HashMap<>();
        body.put("roleCodes", roleCodes);
        body.put("permissionCodes", permissionCodes);
        postVoid("/inner/permissions/bind-roles", body, "权限绑定角色失败");
    }

    private void postVoid(String path, Object body, String fallback) {
        ApiResponse<Void> resp = restClient.post()
                .uri(baseUrl() + path)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(new ParameterizedTypeReference<ApiResponse<Void>>() {});
        if (resp == null || !resp.isSuccess()) {
            throw new InnerClientException(resp == null ? fallback : resp.getMessage(),
                    resp == null ? -1 : resp.getCode());
        }
    }

    private static <T> T requireData(ApiResponse<T> resp, String fallback) {
        if (resp == null || !resp.isSuccess() || resp.getData() == null) {
            throw new InnerClientException(resp == null ? fallback : resp.getMessage(),
                    resp == null ? -1 : resp.getCode());
        }
        return resp.getData();
    }
}
