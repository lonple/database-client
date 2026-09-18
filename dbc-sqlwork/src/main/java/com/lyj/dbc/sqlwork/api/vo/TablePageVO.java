package com.lyj.dbc.sqlwork.api.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 表分页结果。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TablePageVO {

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
