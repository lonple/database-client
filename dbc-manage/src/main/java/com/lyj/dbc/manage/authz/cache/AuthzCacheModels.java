package com.lyj.dbc.manage.authz.cache;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * Redis 中缓存的工作空间授权快照（非最终 allow/deny）。
 */
public final class AuthzCacheModels {

    private AuthzCacheModels() {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class UserAuthzSnapshot {
        private String role;
        private long ver;
        @Builder.Default
        private List<GrantEntry> grants = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class GrantEntry {
        /** ALL / SPECIFIC */
        private String mode;
        private Long connectionId;
        private String scope;
        @Builder.Default
        private List<TableRef> tables = new ArrayList<>();
        @Builder.Default
        private List<String> ops = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TableRef {
        private String database;
        private String schema;
        private String name;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class AssetEntry {
        private Long connectionId;
        private String scope;
        @Builder.Default
        private List<TableRef> tables = new ArrayList<>();
        @Builder.Default
        private List<String> ops = new ArrayList<>();
    }
}
