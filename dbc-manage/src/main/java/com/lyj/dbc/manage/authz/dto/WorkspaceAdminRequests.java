package com.lyj.dbc.manage.authz.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

public final class WorkspaceAdminRequests {

    private WorkspaceAdminRequests() {
    }

    @Data
    public static class CreateWorkspaceRequest {
        @NotBlank
        @Size(max = 128)
        private String name;
        @Size(max = 512)
        private String description;
    }

    @Data
    public static class AddMembersRequest {
        @NotEmpty
        private List<Long> userIds;
    }

    @Data
    public static class AddAssetRequest {
        @NotNull
        private Long connectionId;
        /**
         * CONNECTION / DATABASE / SCHEMA / TABLE（兼容 ALL_TABLES、SPECIFIC_TABLES）。
         */
        @NotBlank
        private String objectScope;
        /** 层级引用；CONNECTION 时可空 */
        private List<ObjectRef> objects;
        /** 兼容旧前端字段名 */
        private List<ObjectRef> tables;
        @NotEmpty
        private List<String> ops;
    }

    @Data
    public static class AddMemberGrantRequest {
        @NotNull
        private Long userId;
        @NotBlank
        private String grantMode;
        private Long connectionId;
        private String objectScope;
        private List<ObjectRef> objects;
        private List<ObjectRef> tables;
        private List<String> ops;
    }

    /**
     * 成员授权三步向导提交：多用户 × 多连接对象范围 × 同一套权限。
     */
    @Data
    public static class BatchMemberGrantRequest {
        @NotEmpty
        private List<Long> userIds;
        @NotEmpty
        @Valid
        private List<GrantTarget> targets;
        @NotEmpty
        private List<String> ops;
    }

    @Data
    public static class GrantTarget {
        @NotNull
        private Long connectionId;
        /** CONNECTION / DATABASE / SCHEMA / TABLE */
        @NotBlank
        private String objectScope;
        private List<ObjectRef> objects;
    }

    @Data
    public static class SetMemberRoleRequest {
        @NotBlank
        private String roleCode;
    }

    /**
     * 授权对象引用。database / schema / name 按 objectScope 选用。
     */
    @Data
    public static class ObjectRef {
        private String database;
        private String schema;
        private String name;
    }
}
