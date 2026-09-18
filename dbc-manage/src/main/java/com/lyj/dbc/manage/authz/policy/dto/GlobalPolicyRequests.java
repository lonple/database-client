package com.lyj.dbc.manage.authz.policy.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * 全局管控请求体。
 */
public final class GlobalPolicyRequests {

    private GlobalPolicyRequests() {
    }

    @Data
    public static class SaveRequest {
        @NotBlank
        private String name;
        @NotEmpty
        private List<String> ops;
        @NotBlank
        private String strategy;
        @NotBlank
        private String workspaceScope;
        private List<Long> workspaceIds;
        private Integer sortNo;
        @NotNull
        private Integer status;
    }
}
