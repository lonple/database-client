package com.lyj.dbc.manage.inner.sqlwork.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

/**
 * 工作台元数据可见性范围（授权并集）。
 * <p>
 * unrestricted=true：连接级全量可见；否则按 scopes 裁剪库 / schema / 表。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ObjectFilter {

    private boolean unrestricted;

    @Builder.Default
    private List<Scope> scopes = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Scope {
        /** DATABASE / SCHEMA / TABLE */
        private String level;
        private String database;
        private String schema;
        /** 表或视图名；仅 TABLE 级有值 */
        private String name;
    }
}
