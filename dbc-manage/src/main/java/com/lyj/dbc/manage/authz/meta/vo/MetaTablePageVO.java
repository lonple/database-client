package com.lyj.dbc.manage.authz.meta.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 与 sqlwork TablePageVO 对齐的表分页结果（manage 代理回传前端）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetaTablePageVO {

    private List<TableItemVO> items;
    private long total;
    private int page;
    private int size;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableItemVO {
        private String schema;
        private String name;
        private String objectType;
    }
}
