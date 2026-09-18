package com.lyj.dbc.manage.authz.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * 工作空间详情（成员 / 资产授权 / 成员授权）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WorkspaceDetailVO {

    private Long id;
    private String name;
    private String description;
    private Long ownerUserId;
    private String spaceType;
    private String myRole;
    private OffsetDateTime updatedAt;

    private List<MemberItem> members;
    private List<AssetItem> assets;
    private List<MemberGrantItem> memberGrants;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MemberItem {
        private Long id;
        private Long userId;
        private String roleCode;
        private OffsetDateTime joinedAt;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ObjectRef {
        private String database;
        private String schema;
        private String name;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AssetItem {
        private Long id;
        private Long connectionId;
        private String connectionName;
        private String objectScope;
        private List<ObjectRef> objects;
        /** 兼容旧前端字段 */
        private List<ObjectRef> tables;
        private List<String> ops;
        private Long createdBy;
        private OffsetDateTime createdAt;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MemberGrantItem {
        private Long id;
        private Long userId;
        private String grantMode;
        private Long connectionId;
        private String connectionName;
        private String objectScope;
        private List<ObjectRef> objects;
        private List<ObjectRef> tables;
        private List<String> ops;
        private Long createdBy;
        private OffsetDateTime createdAt;
    }
}
