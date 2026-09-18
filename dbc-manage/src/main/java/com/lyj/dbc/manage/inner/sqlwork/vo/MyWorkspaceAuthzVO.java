package com.lyj.dbc.manage.inner.sqlwork.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 当前用户在某工作空间的可访问资产与权限（工作台选空间页右侧）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MyWorkspaceAuthzVO {

    private Long workspaceId;
    private String workspaceName;
    private String description;
    private String spaceType;
    /** OWNER / ADMIN / OPERATOR */
    private String role;
    /** 所有者/管理员：隐式拥有空间全部资产 */
    private boolean spaceManager;
    /** 成员授权含 ALL（全部空间资产） */
    private boolean grantAll;

    @Builder.Default
    private List<GrantItem> grants = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GrantItem {
        /** ALL | SPECIFIC | SPACE_ASSET（空间管理员看到的资产条目） */
        private String mode;
        private Long connectionId;
        private String connectionName;
        private String dbType;
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
    public static class TableRef {
        private String database;
        private String schema;
        private String name;
    }
}
