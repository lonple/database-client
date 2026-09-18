package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 元数据浅树（库 → schema → 表）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaTreeVO {

    private List<DatabaseNode> databases;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DatabaseNode {
        private String name;
        private List<SchemaNode> schemas = new ArrayList<>();
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SchemaNode {
        private String name;
        private List<TableNode> tables = new ArrayList<>();
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableNode {
        private String name;
        private String objectType;
    }
}
