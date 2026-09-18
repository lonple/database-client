package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 工作台元数据可见性范围（与 manage 裁决字段一致）。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ObjectFilter {

    private boolean unrestricted;
    private List<Scope> scopes = new ArrayList<>();

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Scope {
        private String level;
        private String database;
        private String schema;
        private String name;
    }
}
