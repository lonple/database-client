package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 当前用户在某工作空间的可访问资产与权限。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MyWorkspaceAuthzVO {

    private Long workspaceId;
    private String workspaceName;
    private String description;
    private String spaceType;
    private String role;
    private boolean spaceManager;
    private boolean grantAll;
    private List<GrantItem> grants = new ArrayList<>();

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GrantItem {
        private String mode;
        private Long connectionId;
        private String connectionName;
        private String dbType;
        private String scope;
        private List<TableRef> tables = new ArrayList<>();
        private List<String> ops = new ArrayList<>();
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableRef {
        private String database;
        private String schema;
        private String name;
    }
}
